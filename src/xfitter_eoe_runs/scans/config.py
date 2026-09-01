"""
Configuration management for scan framework
Reads a workspace config.yaml and provides structured access
"""

from pathlib import Path
from typing import List, Dict, Optional
import warnings
import yaml


class StudyConfig:
    """Configuration for a scan workspace."""

    def __init__(self, config_file: Path, template_root: Path):
        self.config_file = config_file
        self.workspace_dir = config_file.parent
        self.template_root = template_root

        with open(config_file, 'r') as f:
            self.data = yaml.safe_load(f)

        if 'scan_type' not in self.data:
            raise ValueError("config.yaml must specify 'scan_type'")
        if 'template' not in self.data:
            raise ValueError("config.yaml must specify 'template' (a folder name "
                             "under the configured template root, e.g. "
                             "'hera-baseline' or 'giuli')")

        self.scan_type = self.data['scan_type']

    @property
    def datafiles(self) -> List[str]:
        return self.data.get('datafiles', [])

    @property
    def template_dir(self) -> Path:
        """Template folder for this scan, selected by name under template_root.

        Resolved against the explicit template root rather than the workspace.
        Each folder is a self-contained setup:
        steering.txt.j2, parameters.yaml.j2, constants.yaml, unpolarised.wgt.
        """
        root = self.template_root
        d = root / self.data['template']
        if not d.is_dir():
            raise FileNotFoundError(
                f"template folder not found: {d} "
                f"(available: {[p.name for p in sorted(root.iterdir()) if p.is_dir()]})"
            )
        return d

    @property
    def epsilon(self) -> Optional[float]:
        """Global epsilon (optional)."""
        if 'epsilon' in self.data:
            return float(self.data['epsilon'])
        return None

    @property
    def xfitter_tree(self) -> Optional[str]:
        """Build tree under $XFITTER_ROOT for this scan (optional).

        Written into the generated run scripts as `export XFITTER_TREE=...`.
        Condor jobs do not inherit the submitting shell's environment, so
        without this a scan silently runs against whatever .env defaults to.
        """
        return self.data.get('xfitter_tree')

    @property
    def do_errors(self) -> Optional[Dict]:
        """doErrors namespace (optional). Returns dict with method, errdef, iterate."""
        return self.data.get('doErrors')

    @property
    def do_errors_string(self) -> Optional[str]:
        """Build xFitter doErrors multiline string from structured config."""
        de = self.do_errors
        if de is None:
            return None
        method = de['method']
        lines = [method]
        if method == 'Pumplin':
            if 'errdef' in de:
                lines.append(f"SET ERRDEF {de['errdef']}")
            if 'iterate' in de:
                lines.append(f"ITERATE {de['iterate']}")
        return '\n'.join(lines)

    def _expand_systematics(self, entries) -> List[Dict]:
        """Expand ranges and resolve epsilon per-entry (override) or global (fallback).

        Each returned dict has keys: name, type, epsilon, init and
        scale_with_lambda.  The latter defaults to True and is used only by
        lambda scans; setting it to False keeps that source's epsilon fixed
        while the scan parameter is varied.

        `init` is an optional MINUIT warm-start value for the source's nuisance
        parameter (emitted as a `set par` command at fit generation). It is valid
        only for E-type sources and only on single-source entries; it defaults to
        None (xfitter's default of 0, i.e. no command is emitted).
        """
        global_eps = self.epsilon
        result = []
        for entry in entries:
            entry_eps = entry.get('epsilon')
            if entry_eps is not None:
                eps = float(entry_eps)
            elif global_eps is not None:
                eps = global_eps
            else:
                raise ValueError(
                    f"Systematic '{entry['name']}' has no epsilon and no global epsilon defined"
                )

            init = entry.get('init')
            if init is not None:
                if entry.get('type') != 'E':
                    raise ValueError(
                        f"Systematic '{entry['name']}': 'init' is only valid for type 'E' "
                        f"(got type '{entry.get('type')}')"
                    )
                if 'range' in entry:
                    raise ValueError(
                        f"Systematic '{entry['name']}': 'init' is only allowed on "
                        f"single-source entries, not on 'range' entries"
                    )
                init = float(init)

            scale_with_lambda = entry.get('scale_with_lambda', True)
            if not isinstance(scale_with_lambda, bool):
                raise ValueError(
                    f"Systematic '{entry['name']}': 'scale_with_lambda' must "
                    f"be true or false"
                )

            if 'range' in entry:
                prefix, sys_type = entry['name'], entry['type']
                start, end = entry['range'].split('-')
                for i in range(int(start), int(end) + 1):
                    result.append({'name': f"{prefix}{i}", 'type': sys_type,
                                   'epsilon': eps, 'init': None,
                                   'scale_with_lambda': scale_with_lambda})
            else:
                result.append({'name': entry['name'], 'type': entry['type'],
                               'epsilon': eps, 'init': init,
                               'scale_with_lambda': scale_with_lambda})
        return result

    def get(self, key: str, default=None):
        return self.data.get(key, default)


class LambdaScanConfig(StudyConfig):
    """Configuration for lambda-scan workspaces."""

    def __init__(self, config_file: Path, template_root: Path):
        super().__init__(config_file, template_root)

        if self.scan_type != 'lambda-scan':
            raise ValueError(f"Expected scan_type='lambda-scan', got '{self.scan_type}'")

        # Validate required fields
        if 'lambda' not in self.data:
            raise ValueError("Lambda-scan config missing required field: 'lambda'")
        lam = self.data['lambda']
        for key in ('min', 'max', 'step'):
            if key not in lam:
                raise ValueError(f"Lambda-scan config missing 'lambda.{key}'")

        if 'systematics' not in self.data:
            raise ValueError("Lambda-scan config missing required field: 'systematics'")

    @property
    def lambda_min(self) -> float:
        return float(self.data['lambda']['min'])

    @property
    def lambda_max(self) -> float:
        return float(self.data['lambda']['max'])

    @property
    def lambda_step(self) -> float:
        return float(self.data['lambda']['step'])

    @property
    def systematics(self) -> List[Dict]:
        """Get expanded systematics with resolved epsilon and scaling mode."""
        return self._expand_systematics(self.data['systematics'])


class SystematicRankingConfig(StudyConfig):
    """Configuration for systematic-ranking workspaces."""

    def __init__(self, config_file: Path, template_root: Path):
        super().__init__(config_file, template_root)

        if self.scan_type != 'systematic-ranking':
            raise ValueError(f"Expected scan_type='systematic-ranking', got '{self.scan_type}'")

        if 'systematics' not in self.data:
            raise ValueError("Systematic-ranking config missing required field: 'systematics'")

        # Warn if lambda namespace is present (unused in systematic-ranking)
        if 'lambda' in self.data:
            warnings.warn(
                "config.yaml contains 'lambda' namespace but scan_type is 'systematic-ranking' "
                "— lambda settings will be ignored",
                stacklevel=2,
            )

    @property
    def base_systematics(self) -> List[Dict]:
        """EoE sources held on in *every* fit (including the nominal/reference fit).

        Used for higher-order forward-selection scans: e.g. set
        `base_systematics: [{name: sysHZComb1053, type: E, init: -17.38}]` to rank
        all remaining systematics on top of an already-active 1053. Expanded like
        `systematics` ({name, type, epsilon, init}); empty by default.
        """
        return self._expand_systematics(self.data.get('base_systematics', []))

    @property
    def systematics(self) -> List[Dict]:
        """Candidate systematics to rank (expanded, with resolved epsilon).

        Any source already present in `base_systematics` is removed — a base source
        is on in every fit, so it is never also a ranked candidate (this also lets a
        broad `range:` candidate entry overlap the base without manual exclusion).
        """
        base_names = {s['name'] for s in self.base_systematics}
        return [s for s in self._expand_systematics(self.data['systematics'])
                if s['name'] not in base_names]


class PumplinStabilityConfig(StudyConfig):
    """Configuration for pumplin-stability workspaces.

    Scans a 3-axis grid: lambda (EoE strength) x errdef x iterate. A Gaussian
    fit (no &Systematics source) is always added as the lambda=0.0 group.

    The base `eps` is multiplied by lambda to form each source's EoE epsilon
    (same scaling as lambda-scan). `errdef` and `iterate` are the Pumplin
    SET ERRDEF / ITERATE grids set per fit via doErrors.
    """

    def __init__(self, config_file: Path, template_root: Path):
        super().__init__(config_file, template_root)

        if self.scan_type != 'pumplin-stability':
            raise ValueError(f"Expected scan_type='pumplin-stability', got '{self.scan_type}'")

        for key in ('eps', 'lambda', 'errdef', 'iterate', 'systematics'):
            if key not in self.data:
                raise ValueError(f"pumplin-stability config missing required field: '{key}'")

    @property
    def epsilon(self) -> Optional[float]:
        """Base epsilon (named `eps` in this config); reused by _expand_systematics."""
        return float(self.data['eps'])

    @property
    def eps(self) -> float:
        return float(self.data['eps'])

    @property
    def lambdas(self) -> List[float]:
        return [float(x) for x in self.data['lambda']]

    @property
    def errdefs(self) -> List[float]:
        return [float(x) for x in self.data['errdef']]

    @property
    def iterates(self) -> List[int]:
        return [int(x) for x in self.data['iterate']]

    @property
    def errdef_ref(self) -> float:
        """Reference ERRDEF for the errdef-invariance plot normalization."""
        return float(self.data.get('errdef_ref', 0.5))

    @property
    def systematics(self) -> List[Dict]:
        """Expanded systematics; each entry's epsilon is the base eps (scaled by lambda at fit time)."""
        return self._expand_systematics(self.data['systematics'])


class LikelihoodScanConfig(StudyConfig):
    """Configuration for likelihood-scan workspaces.

    The scan_type field in config.yaml must be 'likelihood-scan'.
    Use scan_params_1d to list parameters to scan one at a time.
    A future scan_params_2d key will enable 2D contour scans.
    """

    def __init__(self, config_file: Path, template_root: Path):
        super().__init__(config_file, template_root)

        if self.scan_type != 'likelihood-scan':
            raise ValueError(f"Expected scan_type='likelihood-scan', got '{self.scan_type}'")

        if 'reference_fit' not in self.data:
            raise ValueError("likelihood-scan config missing required field: 'reference_fit'")
        if not any(k in self.data for k in
                   ('scan_params_1d', 'scan_systematics_1d', 'scan_params_2d')):
            raise ValueError(
                "likelihood-scan config must have at least one of "
                "'scan_params_1d', 'scan_systematics_1d', 'scan_params_2d'"
            )

    @property
    def reference_fit(self) -> Path:
        """Absolute reference fit path, resolved relative to the workspace."""
        return (self.workspace_dir / self.data['reference_fit']).resolve()

    @property
    def scan_defaults(self) -> dict:
        return self.data.get('scan_defaults', {'n_sigma': 3, 'npoints': 31})

    @property
    def scan_params_1d(self) -> List[Dict]:
        """PDF parameters to scan: [{name, n_sigma?, npoints?, min?, max?}].
        Fixed via step=0 in the Parameters block."""
        return self.data.get('scan_params_1d', [])

    @property
    def scan_systematics_1d(self) -> List[Dict]:
        """E-type systematics to scan: [{name, n_sigma?, npoints?, min?, max?}].
        Fixed via MINUIT SET PAR / FIX commands (xFitter registers them from &Systematics)."""
        return self.data.get('scan_systematics_1d', [])

    @property
    def scan_params_2d(self) -> List[Dict]:
        """Parameter pairs for 2D contour scans:
        [{pair: [xName, yName], npoints?, n_sigma?, x_range?, y_range?}].

        Each axis name may be a PDF parameter or an E-type systematic; the type is
        inferred from the systematics block. Both axes are fixed at each grid point
        (PDF via step=0, E-type via MINUIT SET PAR / FIX) while the rest are profiled."""
        return self.data.get('scan_params_2d', [])

    @property
    def sigma_levels(self) -> List[float]:
        """Sigma levels at which to draw 2D joint contours (default [1, 2, 3])."""
        return [float(s) for s in self.data.get('sigma_levels', [1, 2, 3])]

    @property
    def systematics(self) -> List[Dict]:
        return self._expand_systematics(self.data.get('systematics', []))

    @property
    def parameter_overrides(self) -> Dict:
        """Optional per-parameter overrides: {name: {value?, step?}}.

        Takes precedence over values read from the reference fit.
        Example in config.yaml:
            parameter_overrides:
              DUbar: {value: 1.9, step: 2.5}
        """
        return self.data.get('parameter_overrides', {})


def load_study_config(run_dir: Path, template_root: Path) -> StudyConfig:
    """
    Load a scan workspace configuration and return the appropriate config object

    Args:
        run_dir: Path to the workspace containing config.yaml
        template_root: Path containing the named scan templates

    Returns:
        StudyConfig subclass instance based on scan_type
    """
    run_dir = Path(run_dir)
    config_file = run_dir / "config.yaml"

    if not config_file.exists():
        raise FileNotFoundError(f"No config.yaml found in {run_dir}")

    with open(config_file, 'r') as f:
        data = yaml.safe_load(f)

    scan_type = data.get('scan_type')

    if scan_type == 'lambda-scan':
        return LambdaScanConfig(config_file, template_root)
    elif scan_type == 'systematic-ranking':
        return SystematicRankingConfig(config_file, template_root)
    elif scan_type == 'pumplin-stability':
        return PumplinStabilityConfig(config_file, template_root)
    elif scan_type == 'likelihood-scan':
        return LikelihoodScanConfig(config_file, template_root)
    else:
        raise ValueError(f"Unknown scan_type: {scan_type}")
