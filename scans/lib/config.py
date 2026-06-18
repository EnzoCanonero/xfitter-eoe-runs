"""
Configuration management for scan framework
Reads study config.yaml and provides structured access
"""

from pathlib import Path
from typing import List, Dict, Optional
import warnings
import yaml


class StudyConfig:
    """Configuration for a scan study"""

    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.study_dir = config_file.parent

        with open(config_file, 'r') as f:
            self.data = yaml.safe_load(f)

        if 'scan_type' not in self.data:
            raise ValueError("config.yaml must specify 'scan_type'")
        if 'template' not in self.data:
            raise ValueError("config.yaml must specify 'template' (a folder name "
                             "under scans/templates/, e.g. 'hera-baseline' or 'giuli')")

        self.scan_type = self.data['scan_type']

    @property
    def datafiles(self) -> List[str]:
        return self.data.get('datafiles', [])

    @property
    def template_dir(self) -> Path:
        """Template folder for this study, selected by name under scans/templates/.

        Resolved against scans/templates/ (not the study dir) so studies can be
        moved/reorganized without breaking. Each folder is a self-contained setup:
        steering.txt.j2, parameters.yaml.j2, constants.yaml, unpolarised.wgt.
        """
        root = Path(__file__).resolve().parent.parent / "templates"
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

        Each returned dict has keys: name, type, epsilon.
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
            if 'range' in entry:
                prefix, sys_type = entry['name'], entry['type']
                start, end = entry['range'].split('-')
                for i in range(int(start), int(end) + 1):
                    result.append({'name': f"{prefix}{i}", 'type': sys_type, 'epsilon': eps})
            else:
                result.append({'name': entry['name'], 'type': entry['type'], 'epsilon': eps})
        return result

    def get(self, key: str, default=None):
        return self.data.get(key, default)


class LambdaScanConfig(StudyConfig):
    """Configuration for lambda-scan studies"""

    def __init__(self, config_file: Path):
        super().__init__(config_file)

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
        """Get expanded systematics with resolved epsilon."""
        return self._expand_systematics(self.data['systematics'])


class SystematicRankingConfig(StudyConfig):
    """Configuration for systematic-ranking studies"""

    def __init__(self, config_file: Path):
        super().__init__(config_file)

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
    def systematics(self) -> List[Dict]:
        """Get expanded systematics with resolved epsilon."""
        return self._expand_systematics(self.data['systematics'])


class PumplinStabilityConfig(StudyConfig):
    """Configuration for pumplin-stability studies.

    Scans a 3-axis grid: lambda (EoE strength) x errdef x iterate. A Gaussian
    fit (no &Systematics source) is always added as the lambda=0.0 group.

    The base `eps` is multiplied by lambda to form each source's EoE epsilon
    (same scaling as lambda-scan). `errdef` and `iterate` are the Pumplin
    SET ERRDEF / ITERATE grids set per fit via doErrors.
    """

    def __init__(self, config_file: Path):
        super().__init__(config_file)

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
    """Configuration for likelihood-scan studies (1D; 2D support to be added).

    The scan_type field in config.yaml must be 'likelihood-scan'.
    Use scan_params_1d to list parameters to scan one at a time.
    A future scan_params_2d key will enable 2D contour scans.
    """

    def __init__(self, config_file: Path):
        super().__init__(config_file)

        if self.scan_type != 'likelihood-scan':
            raise ValueError(f"Expected scan_type='likelihood-scan', got '{self.scan_type}'")

        if 'reference_fit' not in self.data:
            raise ValueError("likelihood-scan config missing required field: 'reference_fit'")
        if 'scan_params_1d' not in self.data and 'scan_systematics_1d' not in self.data:
            raise ValueError(
                "likelihood-scan config must have 'scan_params_1d', "
                "'scan_systematics_1d', or both"
            )

    @property
    def reference_fit(self) -> Path:
        """Absolute path to reference fit directory (resolved relative to study_dir)."""
        return (self.study_dir / self.data['reference_fit']).resolve()

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


def load_study_config(study_dir: Path) -> StudyConfig:
    """
    Load study configuration and return appropriate config object

    Args:
        study_dir: Path to study directory containing config.yaml

    Returns:
        StudyConfig subclass instance based on scan_type
    """
    config_file = study_dir / "config.yaml"

    if not config_file.exists():
        raise FileNotFoundError(f"No config.yaml found in {study_dir}")

    with open(config_file, 'r') as f:
        data = yaml.safe_load(f)

    scan_type = data.get('scan_type')

    if scan_type == 'lambda-scan':
        return LambdaScanConfig(config_file)
    elif scan_type == 'systematic-ranking':
        return SystematicRankingConfig(config_file)
    elif scan_type == 'pumplin-stability':
        return PumplinStabilityConfig(config_file)
    elif scan_type == 'likelihood-scan':
        return LikelihoodScanConfig(config_file)
    else:
        raise ValueError(f"Unknown scan_type: {scan_type}")
