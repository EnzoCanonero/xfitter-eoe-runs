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

        self.scan_type = self.data['scan_type']

    @property
    def datafiles(self) -> List[str]:
        return self.data.get('datafiles', [])

    @property
    def template(self) -> Optional[Path]:
        if 'template' in self.data:
            return Path(self.data['template'])
        return None

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
    else:
        raise ValueError(f"Unknown scan_type: {scan_type}")
