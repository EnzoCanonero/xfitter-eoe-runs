"""
MINUIT output parser
Extracts chi2, parameters, convergence status from fit results
"""

from pathlib import Path
from typing import Dict, Optional, List
import json
import re
import numpy as np
import pandas as pd


class MinuitOutputParser:
    """Parse MINUIT output files into structured data"""

    def __init__(self, fit_dir: Path):
        self.fit_dir = fit_dir
        self.output_dir = fit_dir / "output"
        self.minuit_file = self.output_dir / "minuit.out.txt"

        if not self.minuit_file.exists():
            raise FileNotFoundError(f"MINUIT output not found: {self.minuit_file}")

        with open(self.minuit_file, 'r') as f:
            self.content = f.read()

    def parse_chi2(self) -> Optional[float]:
        """Extract final converged chi2 value from MINUIT output"""
        match = re.search(r'FCN=\s*([\d.]+)\s+FROM MIGRAD\s+STATUS=CONVERGED', self.content)
        if match:
            return float(match.group(1))

        matches = re.findall(r'FCN=\s*([\d.]+)', self.content)
        if matches:
            return float(matches[-1])

        return None

    def parse_convergence_status(self) -> str:
        """Extract MIGRAD convergence status"""
        if "MIGRAD MINIMIZATION HAS CONVERGED" in self.content:
            return 'converged'
        elif "MIGRAD FAILS TO CONVERGE" in self.content or "MIGRAD TERMINATED" in self.content:
            return 'failed'
        else:
            return 'unknown'

    def parse_parameters(self) -> pd.DataFrame:
        """
        Extract parameter central values and errors from EXT PARAMETER tables.

        Uses PARAMETER DEFINITIONS to get untruncated full names (MINUIT truncates
        names to 10 chars in EXT PARAMETER tables), then reads values/errors from
        EXT PARAMETER tables keeping the last (= converged) value per parameter.

        Returns:
            DataFrame with columns: parameter, central_value, error
        """
        name_map = {}
        for m in re.finditer(r"^\s*(\d+)\s+'([^']*?)\s*'", self.content, re.MULTILINE):
            name_map[int(m.group(1))] = m.group(2).strip()

        params = {}
        in_section = False
        for line in self.content.split('\n'):
            if 'EXT PARAMETER' in line:
                in_section = True
                continue
            if in_section:
                if line.strip() == '':
                    in_section = False
                    continue
                parts = line.split()
                if len(parts) >= 4 and parts[0].isdigit():
                    try:
                        num = int(parts[0])
                        val = float(parts[2])
                        err = float(parts[3])
                        full_name = name_map.get(num, parts[1])
                        params[num] = (full_name, val, err)
                    except (ValueError, IndexError):
                        continue

        rows = [
            {'parameter': name, 'central_value': val, 'error': err}
            for _, (name, val, err) in sorted(params.items())
        ]
        return pd.DataFrame(rows)

    def parse_pumplin_parameters(self) -> pd.DataFrame:
        """
        Extract parameter values and Pumplin iterative errors from parsout_0.

        xFitter writes this file when doErrors includes Pumplin. Format:
            <idx>  '<name>'  <value>  <error>  [<min>  <max>]

        Returns:
            DataFrame with columns: parameter, central_value, error
        """
        parsout_file = self.output_dir / "parsout_0"
        if not parsout_file.exists():
            raise FileNotFoundError(f"parsout_0 not found: {parsout_file}")

        rows = []
        pattern = re.compile(r"^\s*(\d+)\s+'([^']+)'\s+([-\d.eE+]+)\s+([-\d.eE+]+)")
        with open(parsout_file, 'r') as f:
            for line in f:
                m = pattern.match(line)
                if m:
                    name = m.group(2).strip()
                    val = float(m.group(3))
                    err = float(m.group(4))
                    rows.append({'parameter': name, 'central_value': val, 'error': err})

        return pd.DataFrame(rows)

    def parse_eigenvectors(self) -> Optional[pd.DataFrame]:
        return None

    def parse_distances(self) -> Optional[pd.DataFrame]:
        return None


class ResultsParser:
    """Parse xFitter Results.txt file"""

    def __init__(self, fit_dir: Path):
        self.fit_dir = fit_dir
        self.results_file = fit_dir / "output" / "Results.txt"

        if not self.results_file.exists():
            raise FileNotFoundError(f"Results.txt not found: {self.results_file}")

        with open(self.results_file, 'r') as f:
            self.content = f.read()
        self.lines = self.content.splitlines()

    def parse_chi2(self) -> Optional[float]:
        match = re.search(r'Chi2 after minimisation\s+([\d.]+)', self.content)
        if match:
            return float(match.group(1))
        return None

    def parse_ndf(self) -> Optional[int]:
        match = re.search(r'Chi2 after minimisation\s+[\d.]+\s+(\d+)', self.content)
        if match:
            return int(match.group(1))
        return None

    def parse_partial_chi2s(self) -> pd.DataFrame:
        rows = []
        pattern = re.compile(r'Dataset\s+(\d+)\s+([\d.]+)\(\s*[+-][\d.]+\)\s+(\d+)\s+(.+)')
        for line in self.lines:
            m = pattern.match(line.strip())
            if m:
                rows.append({
                    'dataset_index': int(m.group(1)),
                    'chi2': float(m.group(2)),
                    'ndata': int(m.group(3)),
                    'dataset_name': m.group(4).strip()
                })
        return pd.DataFrame(rows)

    def parse_systematic_shifts(self) -> pd.DataFrame:
        rows = []
        pattern = re.compile(
            r'^\s*(\d+)\s+(\S+)\s+([-\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(:[\w:]+)'
        )
        for line in self.lines:
            m = pattern.match(line)
            if m:
                rows.append({
                    'index': int(m.group(1)),
                    'name': m.group(2),
                    'shift': float(m.group(3)),
                    'error': float(m.group(4)),
                    'corr_err': float(m.group(5)),
                    'epsilon': float(m.group(6)),
                    'b_theta': float(m.group(7)),
                    'gof_contrib': float(m.group(8)),
                    'sys_type': m.group(9)
                })
        return pd.DataFrame(rows)

    def parse_bartlett_factors(self) -> Dict:
        result = {}
        m = re.search(r'Chi2 Bartlett factor.*?=\s+([\d.]+)', self.content)
        if m:
            result['chi2_bartlett'] = float(m.group(1))
        m = re.search(r'Confidence Intervals Bartlett factor.*?=\s+([\d.]+)', self.content)
        if m:
            result['ci_bartlett'] = float(m.group(1))
        return result


def extract_fit_results(fit_dir: Path, do_errors: Optional[Dict] = None) -> Dict:
    """
    Extract all results from a completed fit

    Args:
        fit_dir: Path to fit directory
        do_errors: Optional doErrors config dict (with 'method' key)

    Returns:
        Dictionary with: chi2, ndf, convergence, parameters, systematic_shifts,
                         partial_chi2s, bartlett
    """
    minuit = MinuitOutputParser(fit_dir)
    results_parser = ResultsParser(fit_dir)

    # Choose parameter parser based on error method
    if do_errors and do_errors.get('method') == 'Pumplin':
        try:
            parameters = minuit.parse_pumplin_parameters()
        except FileNotFoundError:
            # Fall back to EXT PARAMETER if parsout_0 not found
            parameters = minuit.parse_parameters()
    else:
        parameters = minuit.parse_parameters()

    results = {
        'chi2': results_parser.parse_chi2(),
        'ndf': results_parser.parse_ndf(),
        'convergence': minuit.parse_convergence_status(),
        'parameters': parameters,
        'systematic_shifts': results_parser.parse_systematic_shifts(),
        'partial_chi2s': results_parser.parse_partial_chi2s(),
        'bartlett': results_parser.parse_bartlett_factors(),
    }

    return results


def extract_scan_results(scan_dir: Path, scan_type: str,
                         do_errors: Optional[Dict] = None) -> Dict[str, pd.DataFrame]:
    """
    Extract and consolidate results from all fits in a scan

    Args:
        scan_dir: Path to study directory containing fits/
        scan_type: 'lambda-scan' or 'systematic-ranking'
        do_errors: Optional doErrors config dict (with 'method' key)

    Returns:
        Dictionary with 'chi2' and 'parameters' DataFrames
    """
    fits_dir = scan_dir / "runs"

    if not fits_dir.exists():
        raise FileNotFoundError(f"No runs directory found in {scan_dir}")

    all_chi2 = []
    all_parameters = []
    all_shifts = []

    if scan_type == 'likelihood-scan':
        return _extract_likelihood_scan_results(fits_dir)

    # Find all fit subdirectories
    if scan_type == 'lambda-scan':
        fit_dirs = sorted(fits_dir.glob("lambda_*"))
        key_name = 'lambda'
    elif scan_type == 'systematic-ranking':
        fit_dirs = sorted([d for d in fits_dir.iterdir() if d.is_dir()])
        key_name = 'systematic'
    else:
        raise ValueError(f"Unknown scan_type: {scan_type}")

    # Extract nominal fit first (for systematic-ranking shift/uncertainty reference)
    nominal_params = {}
    nominal_chi2 = {}
    nominal_dir = fits_dir / "nominal"
    if scan_type == 'systematic-ranking' and nominal_dir.exists():
        try:
            nominal_results = extract_fit_results(nominal_dir, do_errors=do_errors)
            for _, row in nominal_results['parameters'].iterrows():
                nominal_params[row['parameter']] = (row['central_value'], row['error'])
            nominal_chi2 = {
                'systematic': 'nominal',
                'chi2': nominal_results['chi2'],
                'ndf': nominal_results['ndf'],
                'converged': nominal_results['convergence'] == 'converged',
                'chi2_bartlett': nominal_results['bartlett'].get('chi2_bartlett'),
                'ci_bartlett': nominal_results['bartlett'].get('ci_bartlett'),
            }
            print(f"  Loaded nominal fit: {len(nominal_params)} parameters")
        except Exception as e:
            print(f"Warning: Failed to extract nominal fit from {nominal_dir}: {e}")

    for fit_dir in fit_dirs:
        if fit_dir.name == 'nominal':
            continue

        try:
            results = extract_fit_results(fit_dir, do_errors=do_errors)

            if scan_type == 'lambda-scan':
                key_value = float(fit_dir.name.replace('lambda_', ''))
            else:
                key_value = fit_dir.name

            all_chi2.append({
                key_name: key_value,
                'chi2': results['chi2'],
                'ndf': results['ndf'],
                'converged': results['convergence'] == 'converged',
                'chi2_bartlett': results['bartlett'].get('chi2_bartlett'),
                'ci_bartlett': results['bartlett'].get('ci_bartlett'),
            })

            for _, row in results['parameters'].iterrows():
                all_parameters.append({
                    key_name: key_value,
                    'parameter': row['parameter'],
                    'central_value': row['central_value'],
                    'error': row['error']
                })

            if scan_type == 'systematic-ranking':
                for _, row in results['systematic_shifts'].iterrows():
                    all_shifts.append({
                        key_name: key_value,
                        'sys_name': row['name'],
                        'shift': row['shift'],
                        'error': row['error'],
                        'corr_err': row['corr_err'],
                        'epsilon': row['epsilon'],
                        'b_theta': row['b_theta'],
                        'gof_contrib': row['gof_contrib'],
                        'sys_type': row['sys_type'],
                    })

        except Exception as e:
            print(f"Warning: Failed to extract results from {fit_dir}: {e}")
            continue

    return {
        'chi2': pd.DataFrame(all_chi2),
        'parameters': pd.DataFrame(all_parameters),
        'shifts': pd.DataFrame(all_shifts),
        'nominal_chi2': nominal_chi2,
        'nominal_params': nominal_params,
    }


def _extract_likelihood_scan_results(fits_dir: Path) -> Dict:
    """
    Extract 1D profile likelihood scan results from scan_manifest.json.

    For each scanned parameter, reads chi2 from each fit's Results.txt and
    convergence status from minuit.out.txt.

    Returns dict with key 'scan_1d': {param_name: {'scan_values', 'chi2',
    'delta_chi2', 'converged', 'value_at_minimum', 'error'}}.
    """
    manifest_file = fits_dir / "scan_manifest.json"
    if not manifest_file.exists():
        raise FileNotFoundError(f"scan_manifest.json not found in {fits_dir}")

    with open(manifest_file) as f:
        manifest = json.load(f)

    scan_1d = {}

    for param_name, param_info in manifest['scan_1d'].items():
        scan_values = np.array(param_info['scan_values'])
        fit_dir_names = param_info['fit_dirs']
        ref_val = param_info['value_at_minimum']
        ref_err = param_info['error']

        chi2s = []
        converged_flags = []

        for fit_name in fit_dir_names:
            fit_dir = fits_dir / fit_name
            try:
                results_file = fit_dir / "output" / "Results.txt"
                with open(results_file) as f:
                    content = f.read()
                m = re.search(r'Chi2 after minimisation\s+([\d.]+)', content)
                chi2 = float(m.group(1)) if m else np.nan

                minuit_file = fit_dir / "output" / "minuit.out.txt"
                conv = False
                if minuit_file.exists():
                    with open(minuit_file) as f:
                        mtxt = f.read()
                    conv = "MIGRAD MINIMIZATION HAS CONVERGED" in mtxt
                chi2s.append(chi2)
                converged_flags.append(conv)
            except Exception:
                chi2s.append(np.nan)
                converged_flags.append(False)

        chi2_arr = np.array(chi2s)
        # Normalize to the chi2 at the central scan point (closest value to ref_val).
        central_idx = int(np.argmin(np.abs(scan_values - ref_val)))
        chi2_central = chi2_arr[central_idx]
        if np.isnan(chi2_central):
            chi2_central = np.nanmin(chi2_arr)
        delta_chi2 = chi2_arr - chi2_central

        scan_1d[param_name] = {
            'scan_values': scan_values,
            'chi2': chi2_arr,
            'delta_chi2': delta_chi2,
            'converged': np.array(converged_flags),
            'value_at_minimum': ref_val,
            'error': ref_err,
        }

        n_conv = sum(converged_flags)
        n_total = len(fit_dir_names)
        n_nan = int(np.isnan(chi2_arr).sum())
        print(f"  {param_name}: {n_conv}/{n_total} converged"
              + (f", {n_nan} missing" if n_nan else ""))

    return {'scan_1d': scan_1d}
