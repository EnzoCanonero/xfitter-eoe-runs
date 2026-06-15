"""
Scan runner implementation
Generates fits and submits to Condor based on study config
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from .config import load_study_config, LambdaScanConfig, LikelihoodScanConfig, SystematicRankingConfig
from .templates import (TemplateManager, create_fit_structure,
                         generate_batch_submit, generate_condor_wrapper)

# Free PDF parameters that appear in parameters.yaml.j2 (excludes DEPENDENT: Ag, Auv, Adv).
_PDF_PARAMS = {
    'Bg', 'Cg', 'Agp', 'Bgp', 'Buv', 'Cuv', 'Euv',
    'Bdv', 'Cdv', 'CUbar', 'DUbar', 'ADbar', 'BDbar', 'CDbar',
}


def _patch_parameters(params_file: Path,
                      pdf_params: Dict[str, Dict],
                      scan_fixed_params: Dict[str, float],
                      fix_commands: Optional[Dict[str, Tuple[int, float]]] = None) -> None:
    """
    Patch a rendered parameters.yaml in-place for a likelihood scan fit.

    - pdf_params: {name: {value, step}} — warm-start values from the reference fit
    - scan_fixed_params: {name: value} — PDF parameter to fix at this scan point (step → 0)
    - fix_commands: {name: (minuit_index, value)} — E-type parameters to fix via
      MINUIT 'SET PAR N V' + 'FIX N' commands injected into the Commands block.
      E-type params are never added to the Parameters block; xFitter registers them
      automatically from the &Systematics steering block.
    """
    content = params_file.read_text()

    # Patch PDF parameter values and steps
    for name, pdata in pdf_params.items():
        val = scan_fixed_params.get(name, pdata['value'])
        step = 0.0 if name in scan_fixed_params else pdata['step']

        if name == 'CDbar':
            content = re.sub(
                r'  CDbar:.*\n(?:    [^\n]*\n)*',
                f'  CDbar: [ {val:.8g}, {step:.4g} ]\n',
                content,
            )
        else:
            content = re.sub(
                rf'^([ \t]+{re.escape(name)}[ \t]*:)[ \t]*\[.*?\]',
                rf'\1 [ {val:.8g}, {step:.4g} ]',
                content,
                flags=re.MULTILINE,
            )

    # Inject MINUIT FIX commands for E-type parameters that must be held fixed.
    # These are prepended to the Commands block so MIGRAD never varies them.
    if fix_commands:
        lines = []
        for name, (idx, val) in fix_commands.items():
            lines.append(f'    SET PAR {idx} {val:.8g}')
            lines.append(f'    FIX {idx}')
        fix_block = '\n'.join(lines) + '\n'
        content = content.replace('    call fcn 1\n', fix_block + '    call fcn 1\n', 1)

    params_file.write_text(content)


def run_scan(study_dir: Path, dry_run: bool = False, submit: bool = True):
    """
    Generate fits for a scan study and optionally submit to Condor

    Args:
        study_dir: Path to study directory containing config.yaml
        dry_run: If True, only print what would be done without creating files
        submit: If True, automatically submit jobs to Condor after generating fits
    """
    # Load configuration
    config = load_study_config(study_dir)

    print(f"Scan type: {config.scan_type}")
    print(f"Study directory: {study_dir}")

    if config.do_errors:
        print(f"doErrors: {config.do_errors['method']}")

    # Create runs directory
    fits_dir = study_dir / "runs"

    if config.scan_type == 'lambda-scan':
        _generate_lambda_scan_fits(config, fits_dir, dry_run)
    elif config.scan_type == 'systematic-ranking':
        _generate_systematic_ranking_fits(config, fits_dir, dry_run)
    elif config.scan_type == 'likelihood-scan':
        submit_script = _generate_likelihood_scan_fits(config, fits_dir, dry_run)
    else:
        raise ValueError(f"Unknown scan type: {config.scan_type}")

    if dry_run:
        print("\n[DRY RUN] No files were created")
        return

    import subprocess

    if config.scan_type == 'likelihood-scan':
        # Single-cluster batch submission
        print(f"\nBatch submission script: {submit_script}")
        if submit:
            print(f"\nSubmitting {config.scan_type} batch to Condor...")
            try:
                result = subprocess.run(
                    ['bash', str(submit_script)],
                    capture_output=True, text=True, check=True
                )
                print(result.stdout)
                print("\nBatch submitted successfully!")
                print("Monitor with: condor_q")
            except subprocess.CalledProcessError as e:
                print(f"\nError submitting batch:")
                print(e.stderr)
                raise
        else:
            print(f"\nTo submit: bash {submit_script}")
    else:
        # Per-fit submission (existing behaviour for lambda-scan / systematic-ranking)
        wrapper = generate_condor_wrapper(fits_dir)
        print(f"\nMaster submission script: {wrapper}")
        if submit:
            print("\nSubmitting all fits to Condor...")
            try:
                result = subprocess.run(
                    ['bash', str(wrapper)],
                    cwd=fits_dir,
                    capture_output=True, text=True, check=True
                )
                print(result.stdout)
                print("\nAll fits submitted successfully!")
                print("Monitor jobs with: condor_q")
            except subprocess.CalledProcessError as e:
                print(f"\nError submitting jobs:")
                print(e.stderr)
                raise
        else:
            print("\nTo submit all fits manually:")
            print(f"  cd {fits_dir}")
            print(f"  bash condor_submit_all.sh")


def _generate_lambda_scan_fits(config: LambdaScanConfig, fits_dir: Path, dry_run: bool):
    """Generate fits for lambda-scan"""

    # Get template manager
    template_dir = Path(__file__).parent.parent / "templates"
    templates = TemplateManager(template_dir)

    systematics = config.systematics

    # Generate lambda values
    lambda_vals = np.arange(
        config.lambda_min,
        config.lambda_max + config.lambda_step / 2,
        config.lambda_step
    )

    print(f"\nLambda range: {config.lambda_min} to {config.lambda_max} (step {config.lambda_step})")
    print(f"Number of fits: {len(lambda_vals)}")
    print(f"Number of systematics: {len(systematics)}")
    print(f"\nSystematics:")
    for sys in systematics[:10]:
        print(f"  - {sys['name']} ({sys['type']}, eps={sys['epsilon']})")
    if len(systematics) > 10:
        print(f"  ... and {len(systematics) - 10} more")

    if dry_run:
        print("\nLambda values:")
        for lam in lambda_vals:
            print(f"  lambda = {lam:.2f}")
        return

    # Create fits directory
    fits_dir.mkdir(parents=True, exist_ok=True)

    do_errors = config.do_errors_string

    # Generate fits for each lambda value
    for lam in lambda_vals:
        fit_name = f"lambda_{lam:.1f}"
        fit_dir = fits_dir / fit_name

        print(f"Generating {fit_name}...")

        # Scale each systematic's epsilon by lambda
        scaled_sources = [
            (s['name'], s['type'], s['epsilon'] * lam)
            for s in systematics
        ]

        # Render steering file
        steering = templates.render_steering(
            sources=scaled_sources,
            datafiles=config.datafiles,
            n_iterations=config.get('n_iterations', 2),
            enable_bartlett=config.get('enable_bartlett', True)
        )

        create_fit_structure(fit_dir, steering, "", config.datafiles,
                             do_errors=do_errors)

    print(f"\nCreated {len(lambda_vals)} fits in {fits_dir}")


def _apply_custom_template(fit_dir: Path, template_path: Optional[Path]):
    """Overwrite a fit's parameters.yaml (and sibling constants.yaml) with a
    custom template, if one is configured.

    create_fit_structure always renders the default parameters template; when a
    study specifies `template:` we replace it here. OutputDirectory is repointed
    later by the per-fit submit.sh (it matches on ^OutputDirectory:).
    """
    if template_path is None:
        return
    import shutil
    config_dir = fit_dir / "config"
    shutil.copy(template_path, config_dir / "parameters.yaml")
    # Pick up the constants.yaml sitting next to the template (e.g. custom
    # quark masses), overriding the default one copied by create_fit_structure.
    sibling_constants = template_path.parent / "constants.yaml"
    if sibling_constants.exists():
        shutil.copy(sibling_constants, config_dir / "constants.yaml")


def _generate_systematic_ranking_fits(config: SystematicRankingConfig, fits_dir: Path, dry_run: bool):
    """Generate fits for systematic-ranking"""

    # Get template manager
    template_dir = Path(__file__).parent.parent / "templates"
    templates = TemplateManager(template_dir)

    systematics = config.systematics
    custom_template = config.template
    if custom_template is not None:
        print(f"Using custom parameters template: {custom_template}")

    print(f"\nEpsilon: {config.epsilon}")
    print(f"Number of systematics to test: {len(systematics)}")
    print(f"\nSystematics:")
    for sys in systematics[:10]:
        print(f"  - {sys['name']} ({sys['type']}, eps={sys['epsilon']})")
    if len(systematics) > 10:
        print(f"  ... and {len(systematics) - 10} more")

    if dry_run:
        print(f"\nWill create {len(systematics) + 1} fits ({len(systematics)} systematics + 1 nominal)")
        return

    # Create fits directory
    fits_dir.mkdir(parents=True, exist_ok=True)

    do_errors = config.do_errors_string

    # Generate nominal fit first (no systematics — used as baseline for shift/uncertainty plots)
    print(f"Generating nominal...")
    nominal_steering = templates.render_steering(
        sources=[],
        datafiles=config.datafiles,
        n_iterations=config.get('n_iterations', 2),
        enable_bartlett=config.get('enable_bartlett', True)
    )
    create_fit_structure(fits_dir / "nominal", nominal_steering, "", config.datafiles,
                         do_errors=do_errors)
    _apply_custom_template(fits_dir / "nominal", custom_template)

    # Generate fit for each systematic
    for sys in systematics:
        fit_name = sys['name']
        fit_dir = fits_dir / fit_name

        print(f"Generating {fit_name}...")

        # Single-source list with resolved epsilon
        sources = [(sys['name'], sys['type'], sys['epsilon'])]

        # Render steering file
        steering = templates.render_steering(
            sources=sources,
            datafiles=config.datafiles,
            n_iterations=config.get('n_iterations', 2),
            enable_bartlett=config.get('enable_bartlett', True)
        )

        create_fit_structure(fit_dir, steering, "", config.datafiles,
                             do_errors=do_errors)
        _apply_custom_template(fit_dir, custom_template)

    print(f"\nCreated {len(systematics) + 1} fits in {fits_dir} (including nominal)")


def _build_reference_params(ref_fit_dir: Path,
                             e_type_systematics: List[str]) -> Dict[str, Dict]:
    """
    Read fitted parameter values and errors from a reference fit's MINUIT output.

    MINUIT truncates parameter names to 10 characters.  E-type systematics with
    longer names (e.g. sysHZComb1053) collide when truncated.  They are resolved
    back to full names by matching against the alphabetically-sorted list of
    E-type systematics (MINUIT assigns parameter numbers in alphabetical order).

    Args:
        ref_fit_dir: Path to the reference fit directory (contains output/)
        e_type_systematics: Full names of all E-type systematics in the study config

    Returns:
        dict {full_name: {'value': float, 'error': float}}
    """
    minuit_file = ref_fit_dir / "output" / "minuit.out.txt"
    with open(minuit_file, 'r') as f:
        content = f.read()

    # Parse PARAMETER DEFINITIONS block: {index: truncated_name}
    defs: Dict[int, str] = {}
    for m in re.finditer(r"^\s*(\d+)\s+'([^']*?)\s*'", content, re.MULTILINE):
        defs[int(m.group(1))] = m.group(2).strip()

    # Build truncated_prefix → [sorted full names] from E-type systematics
    trunc_groups: Dict[str, List[str]] = {}
    for full in sorted(e_type_systematics):
        trunc = full[:10]
        trunc_groups.setdefault(trunc, []).append(full)

    # Map each parameter index to a full name
    trunc_counters: Dict[str, int] = {k: 0 for k in trunc_groups}
    index_to_fullname: Dict[int, str] = {}
    for idx in sorted(defs.keys()):
        trunc = defs[idx]
        if trunc in trunc_groups:
            fullnames = trunc_groups[trunc]
            pos = trunc_counters[trunc]
            index_to_fullname[idx] = fullnames[pos] if pos < len(fullnames) else trunc
            trunc_counters[trunc] += 1
        else:
            index_to_fullname[idx] = trunc  # no truncation for short names

    # Parse all EXT PARAMETER tables (last value per index wins = final converged)
    params: Dict[int, Tuple] = {}
    in_section = False
    for line in content.split('\n'):
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
                    idx = int(parts[0])
                    val = float(parts[2])
                    err = float(parts[3])
                    params[idx] = (val, err)
                except (ValueError, IndexError):
                    continue

    result = {}
    for idx, (val, err) in params.items():
        full_name = index_to_fullname.get(idx, defs.get(idx, str(idx)))
        result[full_name] = {'value': val, 'error': err, 'index': idx}

    return result


def _generate_likelihood_scan_fits(config: LikelihoodScanConfig,
                                    fits_dir: Path, dry_run: bool) -> Optional[Path]:
    """
    Generate fits for profile likelihood scans.

    Currently implements 1D: for each parameter in scan_params_1d, generates
    npoints fits with that parameter fixed and all others free (MIGRAD).
    Scan ranges default to [ref_value ± n_sigma * ref_error]; override
    per-parameter with explicit min/max in the config.

    After all fits are created, writes scan_manifest.json and generates a
    single-cluster Condor batch submission (runs/batch/ + runs/submit.sh).

    2D support (scan_params_2d) is reserved for a future extension.

    Returns:
        Path to runs/submit.sh (None in dry-run mode).
    """
    template_dir = Path(__file__).parent.parent / "templates"
    templates = TemplateManager(template_dir)

    systematics = config.systematics
    e_type_names = [s['name'] for s in systematics if s['type'] == 'E']

    print(f"\nReference fit: {config.reference_fit}")
    print(f"E-type systematics (free in MINUIT): {e_type_names}")

    # Read fitted values and errors from reference fit
    ref_params = _build_reference_params(config.reference_fit, e_type_names)

    # Build initial MINUIT starting values from reference fit (override with config)
    initial_params: Dict[str, Dict] = {}
    for name in _PDF_PARAMS:
        if name in ref_params:
            val = ref_params[name]['value']
            err = ref_params[name]['error']
            initial_params[name] = {'value': val, 'step': max(abs(err), 1e-4)}
        else:
            print(f"  WARNING: '{name}' not in reference fit output — template default used")
    for name, override in config.parameter_overrides.items():
        if name in initial_params:
            initial_params[name].update(override)

    # E-type parameters: registered by xFitter automatically from &Systematics.
    # We only need their MINUIT index (for fixing via SET PAR / FIX when scanned).
    e_type_indices: Dict[str, int] = {}
    for name in e_type_names:
        if name in ref_params and 'index' in ref_params[name]:
            e_type_indices[name] = ref_params[name]['index']
        else:
            print(f"  WARNING: MINUIT index for '{name}' not found in reference fit — "
                  f"cannot scan this parameter")

    print(f"\nInitial PDF parameter values (from reference fit):")
    for name, pdata in sorted(initial_params.items()):
        print(f"  {name:8s}: value={pdata['value']:+.6f}, step={pdata['step']:.4f}")
    if e_type_indices:
        print(f"\nE-type parameters (managed by xFitter via &Systematics):")
        for name, idx in e_type_indices.items():
            ref_val = ref_params[name]['value']
            print(f"  {name}: ref_value={ref_val:+.6f}, MINUIT index={idx}")

    defaults = config.scan_defaults
    default_n_sigma = float(defaults.get('n_sigma', 3))
    default_npoints = int(defaults.get('npoints', 31))

    do_errors = config.do_errors_string

    # Build a unified scan list with is_systematic flag
    scan_items = [(p, False) for p in config.scan_params_1d] + \
                 [(p, True)  for p in config.scan_systematics_1d]

    n_pdf  = len(config.scan_params_1d)
    n_syst = len(config.scan_systematics_1d)
    print(f"\n1D scan: {n_pdf} PDF parameter(s), {n_syst} E-type systematic(s)")
    print(f"Defaults: n_sigma={default_n_sigma}, npoints={default_npoints}")

    total_fits = 0
    manifest: Dict = {'scan_1d': {}}
    all_fit_dirs: List[Path] = []

    for scan_param, is_systematic in scan_items:
        name = scan_param['name']

        if name not in ref_params:
            print(f"  WARNING: '{name}' not found in reference fit params — skipping")
            print(f"    Available: {sorted(ref_params.keys())}")
            continue

        if is_systematic and name not in e_type_indices:
            print(f"  WARNING: '{name}' listed in scan_systematics_1d but has no MINUIT "
                  f"index — is it declared as E-type in systematics:? Skipping.")
            continue

        ref_val = ref_params[name]['value']
        ref_err = ref_params[name]['error']

        n_sigma = float(scan_param.get('n_sigma', default_n_sigma))
        npoints = int(scan_param.get('npoints', default_npoints))

        if 'min' in scan_param and 'max' in scan_param:
            lo = float(scan_param['min'])
            hi = float(scan_param['max'])
        else:
            lo = ref_val - n_sigma * ref_err
            hi = ref_val + n_sigma * ref_err

        scan_values = np.linspace(lo, hi, npoints)

        tag = '[syst]' if is_systematic else '[pdf] '
        print(f"  {tag} {name}: [{lo:.4g}, {hi:.4g}] ({npoints} pts, "
              f"ref={ref_val:.4g} ± {ref_err:.4g})")

        if dry_run:
            total_fits += npoints
            continue

        fit_names_for_param = []
        for i, v in enumerate(scan_values):
            fit_name = f"1d_{name}_{i:03d}"
            fit_dir = fits_dir / fit_name

            sources = [(s['name'], s['type'], s['epsilon']) for s in systematics]
            steering = templates.render_steering(
                sources=sources,
                datafiles=config.datafiles,
                n_iterations=config.get('n_iterations', 2),
                enable_bartlett=config.get('enable_bartlett', True),
            )

            create_fit_structure(fit_dir, steering, "", config.datafiles,
                                 do_errors=do_errors)

            if is_systematic:
                # E-type: fixed via MINUIT SET PAR / FIX commands
                fix_cmds = {name: (e_type_indices[name], v)}
                pdf_fixed = {}
            else:
                # PDF param: fixed via step=0 in Parameters block
                fix_cmds = {}
                pdf_fixed = {name: v}

            _patch_parameters(
                fit_dir / "config" / "parameters.yaml",
                pdf_params=initial_params,
                scan_fixed_params=pdf_fixed,
                fix_commands=fix_cmds,
            )
            fit_names_for_param.append(fit_name)
            if not (fit_dir / "output" / "Results.txt").exists():
                all_fit_dirs.append(fit_dir.resolve())

        manifest['scan_1d'][name] = {
            'value_at_minimum': ref_val,
            'error': ref_err,
            'n_sigma': n_sigma,
            'npoints': npoints,
            'lo': lo,
            'hi': hi,
            'scan_values': scan_values.tolist(),
            'fit_dirs': fit_names_for_param,
        }
        total_fits += npoints

    if dry_run:
        print(f"\n[DRY RUN] Would generate {total_fits} fits total")
        return None

    # Write manifest for result collection
    fits_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = fits_dir / "scan_manifest.json"
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)

    # Locate repo root (contains setup_env.sh)
    repo_root = Path(__file__).resolve()
    while repo_root != repo_root.parent:
        if (repo_root / "setup_env.sh").exists():
            break
        repo_root = repo_root.parent

    # Generate single-cluster batch submission
    submit_script = generate_batch_submit(fits_dir, all_fit_dirs, repo_root)

    print(f"\nCreated {total_fits} fits in {fits_dir}")
    print(f"Scan manifest: {manifest_file}")

    return submit_script
