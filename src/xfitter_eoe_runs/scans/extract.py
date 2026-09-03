"""
MINUIT output parser
Extracts chi2, parameters, convergence status from fit results
"""

from pathlib import Path
from typing import Dict, Optional, List, Sequence, Tuple
import json
import re
import numpy as np
import pandas as pd


_NUMERIC_FIELD = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?'
_MINIMISED_RESULT_PATTERN = re.compile(
    rf'^\s*(?:Chi2\s+)?after\s+minimisation\s+'
    rf'({_NUMERIC_FIELD})(?:\s+([+-]?\d+))?',
    re.IGNORECASE | re.MULTILINE,
)


def _parse_minimised_result(content: str) -> Tuple[Optional[float], Optional[int]]:
    """Return minimized chi2 and NDF from either xFitter result heading.

    EoE output uses ``Chi2 after minimisation`` while ordinary fits retain the
    legacy ``After minimisation`` heading.  Missing fields remain ``None`` so
    scan callers can preserve their existing conversion to ``numpy.nan``.
    """
    match = _MINIMISED_RESULT_PATTERN.search(content)
    if not match:
        return None, None
    chi2 = float(match.group(1).replace('D', 'E').replace('d', 'e'))
    ndf = int(match.group(2)) if match.group(2) is not None else None
    return chi2, ndf


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
        chi2, _ = _parse_minimised_result(self.content)
        return chi2

    def parse_ndf(self) -> Optional[int]:
        _, ndf = _parse_minimised_result(self.content)
        return ndf

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
        """Parse the per-source table of Results.txt.

        xFitter prints several table layouts, so punctuation and field count
        identify them:

          extended EoE (9 numbers)
            index name shift error corr_err epsilon r b_tilde b_mutheta
                  gof_contrib lr_contrib type
          compact EoE (6 numbers)
            index name shift error corr_err epsilon b_theta gof_contrib type
          ordinary (``+/-`` separator)
            index name shift +/- error type

        All are parseable for diagnostics. Scan extraction nevertheless
        requires the extended table for every active EoE fit, preventing stale
        pre-fix outputs from entering a new ranking silently. Columns absent
        from a legacy layout are left as None rather than aliased.
        """
        rows = []
        eoe_pattern = re.compile(
            rf'^\s*(\d+)\s+(\S+)\s+((?:{_NUMERIC_FIELD}\s+)+)(:\S+)\s*$'
        )
        ordinary_pattern = re.compile(
            rf'^\s*(\d+)\s+(\S+)\s+({_NUMERIC_FIELD})\s+'
            rf'\+/-\s+({_NUMERIC_FIELD})\s+(:\S+)\s*$'
        )
        for line in self.lines:
            ordinary_match = ordinary_pattern.match(line)
            if ordinary_match:
                rows.append({
                    'index': int(ordinary_match.group(1)),
                    'name': ordinary_match.group(2),
                    'shift': float(
                        ordinary_match.group(3).replace('D', 'E').replace('d', 'e')
                    ),
                    'error': float(
                        ordinary_match.group(4).replace('D', 'E').replace('d', 'e')
                    ),
                    'corr_err': None, 'epsilon': None,
                    'b_theta': None, 'r': None, 'b_tilde': None,
                    'b_mutheta': None, 'gof_contrib': None,
                    'lr_contrib': None,
                    'sys_type': ordinary_match.group(5),
                })
                continue

            eoe_match = eoe_pattern.match(line)
            if not eoe_match:
                continue
            try:
                nums = [
                    float(x.replace('D', 'E').replace('d', 'e'))
                    for x in eoe_match.group(3).split()
                ]
            except ValueError:
                continue
            if len(nums) not in (6, 9):
                continue
            row = {
                'index': int(eoe_match.group(1)),
                'name': eoe_match.group(2),
                'shift': nums[0],
                'error': nums[1],
                'corr_err': nums[2],
                'epsilon': nums[3],
                'sys_type': eoe_match.group(4),
                'b_theta': None, 'r': None, 'b_tilde': None,
                'b_mutheta': None, 'lr_contrib': None,
            }
            if len(nums) == 9:
                row.update({'r': nums[4], 'b_tilde': nums[5], 'b_mutheta': nums[6],
                            'gof_contrib': nums[7], 'lr_contrib': nums[8]})
            elif len(nums) == 6:
                row.update({'b_theta': nums[4], 'gof_contrib': nums[5]})
            rows.append(row)
        columns = [
            'index', 'name', 'shift', 'error', 'corr_err', 'epsilon',
            'b_theta', 'r', 'b_tilde', 'b_mutheta', 'gof_contrib',
            'lr_contrib', 'sys_type',
        ]
        return pd.DataFrame(rows, columns=columns)

    def has_extended_bartlett_table(self) -> bool:
        """Whether Results.txt contains the corrected-build 12-column table."""
        return bool(re.search(
            r'^Index\s+Name\s+Shift\s+Error\s+Corr Err\s+Epsilon\s+r\s+'
            r'b_tilde\s+b_mutheta\s+GoF Contrib\s+LR Contrib\s+Type\s*$',
            self.content, re.MULTILINE,
        ))

    def bartlett_failed(self) -> bool:
        return 'Bartlett factors UNAVAILABLE' in self.content

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
        'bartlett_extended': results_parser.has_extended_bartlett_table(),
        'bartlett_failed': results_parser.bartlett_failed(),
    }

    return results


def _fit_has_active_eoe(fit_dir: Path) -> bool:
    """Return true when the generated steering activates a non-zero EoE."""
    steering = fit_dir / 'config' / 'steering.txt'
    if not steering.is_file():
        return False
    num = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?'
    return any(
        float(m.group(1)) != 0.0
        for m in re.finditer(rf'@eps\s*=\s*({num})', steering.read_text(), re.I)
    )


def _validate_bartlett_output(results: Dict, fit_dir: Path, active_eoe: bool):
    """Fail closed when an EoE fit lacks corrected-build diagnostics."""
    if not active_eoe:
        return
    if not results.get('bartlett_extended'):
        raise RuntimeError(
            f"active EoE fit lacks the 12-column Bartlett table: {fit_dir}"
        )
    if results.get('bartlett_failed'):
        raise RuntimeError(f"Bartlett calculation failed: {fit_dir}")
    factor = results.get('bartlett', {}).get('chi2_bartlett')
    if factor is None or not np.isfinite(factor) or factor <= 0.0:
        raise RuntimeError(
            f"active EoE fit lacks a valid chi2 Bartlett factor: {fit_dir}"
        )


def _validate_fit_output(results: Dict, fit_dir: Path):
    """Reject incomplete output while retaining completed non-converged fits."""
    chi2 = results.get('chi2')
    if chi2 is None or not np.isfinite(float(chi2)):
        raise RuntimeError(f"fit lacks a finite minimized chi2: {fit_dir}")
    if results.get('ndf') is None:
        raise RuntimeError(f"fit lacks its number of degrees of freedom: {fit_dir}")


def _corrected_chi2(results: Dict, active_eoe: bool = False):
    """Bartlett-corrected goodness-of-fit chi2 = chi2 * c_chi2.

    This is what xfitter itself prints as 'Corrected Chi2'
    (chi2out_print = chi2out * c_bart_chi2 in fcn.f). We recompute it from the
    raw chi2 and the printed factor rather than parsing that line, because the
    line is only written when errors-on-errors are active.  A genuinely
    Gaussian fit therefore uses a unit factor; active EoE fits are validated
    above and never receive this fallback.

    Only meaningful where the chi2 IS a goodness-of-fit, i.e. for the
    systematic-ranking and lambda scans. Likelihood scans report a delta-chi2
    profile, which is a confidence-interval statistic corrected by b_mu (the
    c_CI factor), not by b_q -- they must keep the minimized chi2.
    """
    chi2 = results.get('chi2')
    if chi2 is None or (isinstance(chi2, float) and np.isnan(chi2)):
        return chi2
    factor = results.get('bartlett', {}).get('chi2_bartlett')
    if active_eoe:
        return chi2 * factor
    return chi2 * (factor if factor is not None else 1.0)


def extract_scan_results(run_dir: Path, scan_type: str,
                         do_errors: Optional[Dict] = None) -> Dict[str, pd.DataFrame]:
    """
    Extract and consolidate results from all fits in a scan

    Args:
        run_dir: Path to the runtime workspace containing runs/
        scan_type: 'lambda-scan' or 'systematic-ranking'
        do_errors: Optional doErrors config dict (with 'method' key)

    Returns:
        Dictionary with 'chi2' and 'parameters' DataFrames
    """
    fits_dir = run_dir / "runs"

    if not fits_dir.exists():
        raise FileNotFoundError(f"No runs directory found in {run_dir}")

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
        fit_dirs = sorted([
            d for d in fits_dir.iterdir()
            if d.is_dir() and d.name != 'batch'
        ])
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
            _validate_fit_output(nominal_results, nominal_dir)
            nominal_active_eoe = _fit_has_active_eoe(nominal_dir)
            _validate_bartlett_output(
                nominal_results, nominal_dir, nominal_active_eoe
            )
            for _, row in nominal_results['parameters'].iterrows():
                nominal_params[row['parameter']] = (row['central_value'], row['error'])
            nominal_chi2 = {
                'systematic': 'nominal',
                'chi2': nominal_results['chi2'],
                'chi2_corrected': _corrected_chi2(
                    nominal_results, nominal_active_eoe
                ),
                'ndf': nominal_results['ndf'],
                'converged': nominal_results['convergence'] == 'converged',
                'chi2_bartlett': nominal_results['bartlett'].get('chi2_bartlett'),
                'ci_bartlett': nominal_results['bartlett'].get('ci_bartlett'),
            }
            print(f"  Loaded nominal fit: {len(nominal_params)} parameters")
        except Exception as e:
            raise RuntimeError(
                f"Failed to extract nominal fit from {nominal_dir}: {e}"
            ) from e

    failures = []
    for fit_dir in fit_dirs:
        if fit_dir.name == 'nominal':
            continue

        try:
            results = extract_fit_results(fit_dir, do_errors=do_errors)
            _validate_fit_output(results, fit_dir)
            active_eoe = _fit_has_active_eoe(fit_dir)
            _validate_bartlett_output(results, fit_dir, active_eoe)

            if scan_type == 'lambda-scan':
                key_value = float(fit_dir.name.replace('lambda_', ''))
            else:
                key_value = fit_dir.name

            all_chi2.append({
                key_name: key_value,
                'chi2': results['chi2'],
                'chi2_corrected': _corrected_chi2(results, active_eoe),
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
                        'r': row['r'],
                        'b_tilde': row['b_tilde'],
                        'b_mutheta': row['b_mutheta'],
                        'gof_contrib': row['gof_contrib'],
                        'lr_contrib': row['lr_contrib'],
                        'sys_type': row['sys_type'],
                    })

        except Exception as e:
            failures.append(f"{fit_dir.name}: {e}")
            continue

    if failures:
        preview = '\n  '.join(failures[:10])
        more = f"\n  ... and {len(failures) - 10} more" if len(failures) > 10 else ''
        raise RuntimeError(
            f"Failed to extract {len(failures)} scan fit(s); refusing a partial "
            f"ranking:\n  {preview}{more}"
        )

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

    for param_name, param_info in manifest.get('scan_1d', {}).items():
        scan_values = np.array(param_info['scan_values'])
        fit_dir_names = param_info['fit_dirs']
        ref_val = param_info['value_at_minimum']
        ref_err = param_info['error']

        # NB: deliberately the MINIMIZED chi2, not the Bartlett-corrected one.
        # A likelihood scan measures a delta-chi2 profile, i.e. a
        # profile-likelihood ratio used for confidence intervals; the GVM
        # corrects that with b_mu (the c_CI factor), not with the
        # goodness-of-fit b_q. Applying c_chi2 here would be wrong.
        chi2s = []
        converged_flags = []

        for fit_name in fit_dir_names:
            fit_dir = fits_dir / fit_name
            try:
                results_file = fit_dir / "output" / "Results.txt"
                with open(results_file) as f:
                    content = f.read()
                chi2, _ = _parse_minimised_result(content)
                chi2 = chi2 if chi2 is not None else np.nan

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

    # ── 2D grid extraction ──────────────────────────────────────────────────
    def _read_chi2_status(fit_dir: Path):
        # As above: the MINIMIZED chi2 by design. This feeds a 2D delta-chi2
        # contour (a confidence region), which the GVM corrects with b_mu, not
        # with the goodness-of-fit b_q.
        chi2 = np.nan
        conv = False
        status = 'missing'
        final_fcn = np.nan
        try:
            parsed_chi2, _ = _parse_minimised_result(
                (fit_dir / "output" / "Results.txt").read_text()
            )
            chi2 = parsed_chi2 if parsed_chi2 is not None else np.nan
        except Exception:
            chi2 = np.nan
        try:
            mf = fit_dir / "output" / "minuit.out.txt"
            if mf.exists():
                text = mf.read_text(errors='replace')
                matches = re.findall(
                    r'FCN=\s*([-+0-9.Ee]+)\s+FROM MIGRAD\s+STATUS=([A-Z ]+)',
                    text,
                )
                if matches:
                    final_fcn = float(matches[-1][0])
                    status = ' '.join(matches[-1][1].split()).lower().replace(' ', '_')
                    conv = status == 'converged'
                elif "MIGRAD MINIMIZATION HAS CONVERGED" in text:
                    status = 'converged_text_only'
                    conv = True
                else:
                    status = 'no_migrad_status'
                if not np.isfinite(chi2) and np.isfinite(final_fcn):
                    chi2 = final_fcn
        except Exception:
            conv = False
            status = 'unreadable_minuit'
        return chi2, conv, status

    scan_2d = {}
    for pair_key, info in manifest.get('scan_2d', {}).items():
        xs = np.array(info['x_values'])
        ys = np.array(info['y_values'])
        grid = info['fit_grid']  # grid[i][j] -> fit dir name
        nx, ny = len(xs), len(ys)
        chi2 = np.full((nx, ny), np.nan)
        conv = np.zeros((nx, ny), dtype=bool)
        status = np.full((nx, ny), 'missing', dtype=object)
        for i in range(nx):
            for j in range(ny):
                c, cv, st = _read_chi2_status(fits_dir / grid[i][j])
                chi2[i, j] = c
                conv[i, j] = cv
                status[i, j] = st

        x_ref = info.get('x_ref')
        y_ref = info.get('y_ref')
        if x_ref is not None and y_ref is not None:
            ix_ref = int(np.argmin(np.abs(xs - float(x_ref))))
            iy_ref = int(np.argmin(np.abs(ys - float(y_ref))))
            chi2_reference = chi2[ix_ref, iy_ref]
        else:
            ix_ref = iy_ref = None
            chi2_reference = np.nan

        if not np.isfinite(chi2_reference):
            valid = chi2[conv & np.isfinite(chi2)]
            chi2_reference = float(np.min(valid)) if valid.size else float(np.nanmin(chi2))

        delta_chi2 = chi2 - chi2_reference

        scan_2d[pair_key] = {
            'x_name': info['x_name'], 'y_name': info['y_name'],
            'x_values': xs, 'y_values': ys,
            'x_ref': x_ref, 'y_ref': y_ref,
            'x_err': info.get('x_err'), 'y_err': info.get('y_err'),
            'ix_ref': ix_ref, 'iy_ref': iy_ref,
            'chi2_reference': chi2_reference,
            'sigma_levels': info.get('sigma_levels', [1, 2, 3]),
            'chi2': chi2, 'delta_chi2': delta_chi2,
            'converged': conv, 'status': status,
        }
        print(f"  {pair_key}: {int(conv.sum())}/{nx * ny} converged")

    return {'scan_1d': scan_1d, 'scan_2d': scan_2d}


# ── Pumplin-stability interval extraction ───────────────────────────────────
# Pumplin error analysis prints, per parameter, the allowed up/down displacement
# (interval half-width) in an "XRANGE: find allowed displacements" block. We parse
# the half-width per (lambda, errdef, iterate, parameter) across the run grid.

_PUMPLIN_RUN_DIR = re.compile(r"errdef(?P<err>\d+p\d)_iter(?P<it>\d+)")
_PUMPLIN_PARAM_DEF = re.compile(
    r"^\s*(\d+)\s+'?([A-Za-z0-9_]+)\s*'?\s+(?:constant|[-+0-9.Ee]+)"
)
_PUMPLIN_XRANGE_PARAM = re.compile(
    r"Par=\s*(\d+)\s+TruePar=\s*(\d+)\s+at\s+([\d.Ee+\-]+)\s+\+/-\s+([\d.Ee+\-]+)"
)


def _resolve_ordered_minuit_definitions(definitions: Dict[int, str],
                                        target_names: Sequence[str]) -> Dict[int, str]:
    """Resolve truncated MINUIT names by definition-index occurrence.

    ``target_names`` must be an ordered sequence (for Pumplin, the configured
    parameter order). Multiple long names can share the same ten-character
    MINUIT spelling; their occurrences in the parameter-definition table are
    paired with the corresponding targets in sequence order.
    """
    if isinstance(target_names, (set, frozenset)):
        raise TypeError("target_names must be an ordered sequence, not a set")

    trunc_groups: Dict[str, List[str]] = {}
    for target in target_names:
        trunc_groups.setdefault(target[:10], []).append(target)

    counters = {prefix: 0 for prefix in trunc_groups}
    resolved: Dict[int, str] = {}
    for index in sorted(definitions):
        truncated = definitions[index].strip()
        candidates = trunc_groups.get(truncated)
        if candidates is None:
            resolved[index] = truncated
            continue
        occurrence = counters[truncated]
        resolved[index] = (
            candidates[occurrence]
            if occurrence < len(candidates)
            else truncated
        )
        counters[truncated] += 1
    return resolved


def extract_pumplin_widths(runs_dir: Path, params: Sequence[str]):
    """Parse completed Pumplin interval widths from a pumplin-stability runs/ tree.

    Expects runs laid out as runs/lambda_<v>/errdef<X>p<Y>_iter<NN>/output/minuit.out.txt.

    Returns (widths, incomplete):
      widths: {(lambda: float, errdef: float, iterate: int, param: str): half_width}
      incomplete: [str] run dirs (relative to runs_dir) missing a complete Pumplin block.
    """
    import math

    if isinstance(params, (set, frozenset)):
        raise TypeError("params must be an ordered sequence, not a set")
    params = tuple(params)

    widths: Dict = {}
    incomplete: List[str] = []

    for minuit_file in sorted(runs_dir.glob("lambda_*/errdef*_iter*/output/minuit.out.txt")):
        run_dir = minuit_file.parents[1]
        lam_name = minuit_file.parents[2].name  # lambda_0.5
        run_match = _PUMPLIN_RUN_DIR.match(run_dir.name)
        if not lam_name.startswith("lambda_") or not run_match:
            continue
        try:
            lam = float(lam_name.replace("lambda_", ""))
        except ValueError:
            continue

        text = minuit_file.read_text(errors="replace")
        is_complete = (
            "XRANGE: find allowed displacements" in text
            and "ERROR MATRIX FROM ITERATE" in text
        )
        if not is_complete:
            incomplete.append(str(run_dir.relative_to(runs_dir)))
            continue

        raw_names: Dict[int, str] = {}
        in_definitions = False
        for line in text.splitlines():
            if "PARAMETER DEFINITIONS" in line:
                in_definitions = True
                continue
            if in_definitions and line.strip().startswith("**********"):
                in_definitions = False
            if in_definitions:
                m = _PUMPLIN_PARAM_DEF.match(line)
                if m:
                    raw_names[int(m.group(1))] = m.group(2)

        names = _resolve_ordered_minuit_definitions(raw_names, params)

        errdef = float(run_match.group("err").replace("p", "."))
        iterate = int(run_match.group("it"))
        for m in _PUMPLIN_XRANGE_PARAM.finditer(text):
            name = names.get(int(m.group(2)))
            if name not in params:
                continue
            width = float(m.group(4).replace("D", "E"))
            if math.isfinite(width) and width > 0:
                widths[(lam, errdef, iterate, name)] = width

    return widths, incomplete
