"""
Scan runner implementation
Generates fits and submits to Condor based on study config
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from .config import (load_study_config, LambdaScanConfig, LikelihoodScanConfig,
                     SystematicRankingConfig, PumplinStabilityConfig)
from .templates import (TemplateManager, create_fit_structure,
                         generate_batch_submit)

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


def _eoe_param_indices(parameters_yaml_text: str,
                       e_source_names: List[str]) -> Dict[str, int]:
    """Map each E-type EoE source to its 1-based MINUIT parameter number.

    xfitter registers every key in the `Parameters:` block (including DEPENDENT,
    constant and derived ones) as parameters 1..Np, then appends each `:E`
    systematic in **ListOfSources declaration order** (verified against MINUIT
    output: 22 PDF params, then sysHZComb1053 = #23, proc_tb21 = #24 for
    ListOfSources = '…1053', '…tb21'). We replicate that so `set par <N>` can
    target a source without needing a prior fit to read indices.

    Args:
        parameters_yaml_text: rendered parameters.yaml content for the fit.
        e_source_names: the fit's :E source names, in ListOfSources order.

    Returns:
        {source_name: minuit_index}.
    """
    m = re.search(r'^Parameters:\s*$(.*?)^Parameterisations:',
                  parameters_yaml_text, re.MULTILINE | re.DOTALL)
    block = m.group(1) if m else parameters_yaml_text
    # Top-level keys are exactly two-space indented (nested CDbar value/step are deeper).
    n_pdf = len(re.findall(r'^  (\w+)\s*:', block, re.MULTILINE))
    return {name: n_pdf + i + 1 for i, name in enumerate(e_source_names)}


def _inject_init_commands(params_file: Path, init_by_index: Dict[int, float]) -> None:
    """Warm-start E-type EoE nuisances via MINUIT `set par <idx> <val>` commands.

    Lines are inserted before the `    call fcn 1\n` anchor in the Commands block
    (same mechanism as _patch_parameters, but without FIX). Zero/None values are
    skipped, so an unset/explicit-0 init is a no-op (xfitter's default).
    """
    cmds = {idx: val for idx, val in init_by_index.items() if val}
    if not cmds:
        return
    content = params_file.read_text()
    block = ''.join(f'    set par {idx} {val:.8g}\n' for idx, val in sorted(cmds.items()))
    content = content.replace('    call fcn 1\n', block + '    call fcn 1\n', 1)
    params_file.write_text(content)


def _apply_source_inits(fit_dir: Path, sources: List[Dict]) -> None:
    """Inject init `set par` commands for a fit's E-type sources that carry an init.

    `sources` are expanded systematics dicts ({name, type, epsilon, init}). No-op
    when none have a non-zero init. Used by the from-scratch generators (systematic
    -ranking, lambda-scan, pumplin-stability), which have no reference fit to read
    MINUIT indices from.
    """
    e_sources = [s['name'] for s in sources if s.get('type') == 'E']
    e_init = {s['name']: s['init'] for s in sources
              if s.get('type') == 'E' and s.get('init')}
    if not e_init:
        return
    params_file = fit_dir / "config" / "parameters.yaml"
    # Index must be computed over ALL :E sources in the fit (their MINUIT numbers
    # depend on the full set), then we set par only for the init-bearing ones.
    idx = _eoe_param_indices(params_file.read_text(), e_sources)
    _inject_init_commands(params_file, {idx[n]: e_init[n] for n in e_init})


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
        submit_script = _generate_lambda_scan_fits(config, fits_dir, dry_run)
    elif config.scan_type == 'systematic-ranking':
        submit_script = _generate_systematic_ranking_fits(config, fits_dir, dry_run)
    elif config.scan_type == 'pumplin-stability':
        submit_script = _generate_pumplin_stability_fits(config, fits_dir, dry_run)
    elif config.scan_type == 'likelihood-scan':
        submit_script = _generate_likelihood_scan_fits(config, fits_dir, dry_run)
    else:
        raise ValueError(f"Unknown scan type: {config.scan_type}")

    if dry_run:
        print("\n[DRY RUN] No files were created")
        return

    import subprocess

    # Single-cluster batch submission (uniform across all scan types)
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


def _fmt_eps(x: float) -> str:
    """Clean numeric formatting for an EoE epsilon in a steering source string."""
    return f"{x:.10g}"


def _pumplin_grid_name(errdef: float, iterate: int) -> str:
    """Run-dir leaf name, e.g. errdef0p5_iter10 (matches the legacy layout)."""
    return f"errdef{errdef:.1f}".replace('.', 'p') + f"_iter{int(iterate):02d}"


def _generate_pumplin_stability_fits(config: PumplinStabilityConfig, fits_dir: Path, dry_run: bool):
    """Generate fits for a pumplin-stability scan: lambda x errdef x iterate.

    A Gaussian fit (no &Systematics source) is always added as the lambda_0.0 group.
    Each non-Gaussian source's epsilon = base eps * lambda. ERRDEF/ITERATE are set
    per fit via the Pumplin doErrors block.
    """
    template_dir = config.template_dir
    templates = TemplateManager(template_dir)

    systematics = config.systematics
    lambdas = config.lambdas
    errdefs = config.errdefs
    iterates = config.iterates
    eps = config.eps

    # (lambda_value, source_systematics) — Gaussian first, then each lambda
    groups = [(0.0, [])] + [(lam, systematics) for lam in lambdas]
    n_fits = len(groups) * len(errdefs) * len(iterates)

    print(f"\nPumplin-stability grid:")
    print(f"  lambda (Gaussian + vector): {[0.0] + lambdas}")
    print(f"  errdef:  {errdefs}")
    print(f"  iterate: {iterates}")
    print(f"  base eps: {eps}")
    print(f"  systematics: {[(s['name'], s['type']) for s in systematics]}")
    print(f"  total fits: {n_fits}")

    if dry_run:
        print("\nExample source strings:")
        for lam in lambdas:
            for s in systematics[:1]:
                print(f"  lambda={lam}: '{s['name']}:{s['type']}@eps={_fmt_eps(s['epsilon'] * lam)}'")
        print("  lambda=0.0: Gaussian (no &Systematics source)")
        return None

    fits_dir.mkdir(parents=True, exist_ok=True)

    all_fit_dirs: List[Path] = []
    for lam, syslist in groups:
        scaled_sources = [
            (s['name'], s['type'], _fmt_eps(s['epsilon'] * lam)) for s in syslist
        ]
        lam_name = f"lambda_{lam:.1f}"
        print(f"Generating {lam_name} ({len(errdefs) * len(iterates)} fits)...")
        for errdef in errdefs:
            for iterate in iterates:
                fit_dir = fits_dir / lam_name / _pumplin_grid_name(errdef, iterate)
                do_errors = f"Pumplin\nSET ERRDEF {errdef}\nITERATE {iterate}"
                steering = templates.render_steering(
                    sources=scaled_sources,
                    datafiles=config.datafiles,
                    n_iterations=config.get('n_iterations', 2),
                    enable_bartlett=config.get('enable_bartlett', True),
                    q2_cut=config.get('q2_cut', 3.5),
                )
                create_fit_structure(fit_dir, steering, "", config.datafiles,
                                     template_dir=template_dir, do_errors=do_errors,
                             xfitter_tree=config.xfitter_tree)
                _apply_source_inits(fit_dir, syslist)
                all_fit_dirs.append(fit_dir.resolve())

    print(f"\nCreated {len(all_fit_dirs)} fits in {fits_dir}")
    return generate_batch_submit(
        fits_dir, all_fit_dirs, config.xfitter_tree,
        request_memory=str(config.get('request_memory', '2GB')),
    )


def _generate_lambda_scan_fits(config: LambdaScanConfig, fits_dir: Path, dry_run: bool):
    """Generate fits for lambda-scan"""

    # Template folder selected by the study config's `template:` field
    template_dir = config.template_dir
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
    n_scaled = sum(s['scale_with_lambda'] for s in systematics)
    n_fixed = len(systematics) - n_scaled
    if n_scaled == 0:
        raise ValueError(
            "Lambda scan has no source with scale_with_lambda: true"
        )

    print(f"Number of systematics: {len(systematics)} "
          f"({n_scaled} scaled, {n_fixed} fixed)")
    print(f"\nSystematics:")
    for sys in systematics[:10]:
        mode = "scaled" if sys['scale_with_lambda'] else "fixed"
        print(f"  - {sys['name']} ({sys['type']}, eps={sys['epsilon']}, {mode})")
    if len(systematics) > 10:
        print(f"  ... and {len(systematics) - 10} more")

    if dry_run:
        print("\nLambda values:")
        for lam in lambda_vals:
            print(f"  lambda = {lam:.2f}")
        return None

    # Create fits directory
    fits_dir.mkdir(parents=True, exist_ok=True)

    do_errors = config.do_errors_string

    # Generate fits for each lambda value
    all_fit_dirs: List[Path] = []
    for lam in lambda_vals:
        fit_name = f"lambda_{lam:.1f}"
        fit_dir = fits_dir / fit_name

        print(f"Generating {fit_name}...")

        # Scale only the requested sources.  Sources marked
        # scale_with_lambda: false retain their nominal epsilon at every point.
        scaled_sources = [
            (s['name'], s['type'],
             _fmt_eps(s['epsilon'] * lam
                      if s['scale_with_lambda'] else s['epsilon']))
            for s in systematics
        ]

        # Render steering file
        steering = templates.render_steering(
            sources=scaled_sources,
            datafiles=config.datafiles,
            n_iterations=config.get('n_iterations', 2),
            enable_bartlett=config.get('enable_bartlett', True),
            q2_cut=config.get('q2_cut', 3.5)
        )

        create_fit_structure(fit_dir, steering, "", config.datafiles,
                             template_dir=template_dir, do_errors=do_errors,
                             xfitter_tree=config.xfitter_tree)
        _apply_source_inits(fit_dir, systematics)
        all_fit_dirs.append(fit_dir.resolve())

    print(f"\nCreated {len(lambda_vals)} fits in {fits_dir}")
    return generate_batch_submit(
        fits_dir, all_fit_dirs, config.xfitter_tree,
        request_memory=str(config.get('request_memory', '2GB')),
    )


def _generate_systematic_ranking_fits(config: SystematicRankingConfig, fits_dir: Path, dry_run: bool):
    """Generate fits for systematic-ranking"""

    # Template folder selected by the study config's `template:` field
    template_dir = config.template_dir
    templates = TemplateManager(template_dir)

    systematics = config.systematics
    base = config.base_systematics
    base_sources = [(s['name'], s['type'], s['epsilon']) for s in base]
    print(f"Q2 cut: {config.get('q2_cut', 3.5)}")

    print(f"\nEpsilon: {config.epsilon}")
    if base:
        print(f"Base EoE sources (held on in every fit): "
              f"{[(s['name'], s['epsilon'], s['init']) for s in base]}")
    print(f"Number of systematics to test: {len(systematics)}")
    print(f"\nSystematics:")
    for sys in systematics[:10]:
        print(f"  - {sys['name']} ({sys['type']}, eps={sys['epsilon']})")
    if len(systematics) > 10:
        print(f"  ... and {len(systematics) - 10} more")

    if dry_run:
        print(f"\nWill create {len(systematics) + 1} fits ({len(systematics)} systematics + 1 nominal)")
        return None

    # Create fits directory
    fits_dir.mkdir(parents=True, exist_ok=True)

    do_errors = config.do_errors_string

    def _render(sources):
        return templates.render_steering(
            sources=sources,
            datafiles=config.datafiles,
            n_iterations=config.get('n_iterations', 2),
            enable_bartlett=config.get('enable_bartlett', True),
            q2_cut=config.get('q2_cut', 3.5),
        )

    # Nominal/reference fit = base sources only (no candidate). With an empty base
    # this is the usual Gaussian nominal; with a base set it is the lower-order fit.
    print(f"Generating nominal...")
    create_fit_structure(fits_dir / "nominal", _render(base_sources), "", config.datafiles,
                         template_dir=template_dir, do_errors=do_errors,
                             xfitter_tree=config.xfitter_tree)
    _apply_source_inits(fits_dir / "nominal", base)
    all_fit_dirs: List[Path] = [(fits_dir / "nominal").resolve()]

    # Generate fit for each candidate systematic, on top of the base sources.
    for sys in systematics:
        fit_name = sys['name']
        fit_dir = fits_dir / fit_name

        print(f"Generating {fit_name}...")

        fit_systematics = base + [sys]
        sources = [(s['name'], s['type'], s['epsilon']) for s in fit_systematics]

        create_fit_structure(fit_dir, _render(sources), "", config.datafiles,
                             template_dir=template_dir, do_errors=do_errors,
                             xfitter_tree=config.xfitter_tree)
        _apply_source_inits(fit_dir, fit_systematics)
        all_fit_dirs.append(fit_dir.resolve())

    print(f"\nCreated {len(systematics) + 1} fits in {fits_dir} (including nominal)")
    return generate_batch_submit(
        fits_dir, all_fit_dirs, config.xfitter_tree,
        request_memory=str(config.get('request_memory', '2GB')),
    )


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
    # Template folder selected by the study config's `template:` field
    template_dir = config.template_dir
    templates = TemplateManager(template_dir)

    systematics = config.systematics
    e_type_names = [s['name'] for s in systematics if s['type'] == 'E']

    print(f"\nReference fit: {config.reference_fit}")
    print(f"E-type systematics (free in MINUIT): {e_type_names}")

    # Read fitted values and errors from reference fit
    ref_params = _build_reference_params(config.reference_fit, e_type_names)

    # Build initial MINUIT starting values from reference fit (override with config).
    # PDF params are every fitted (variable) parameter in the reference fit that is
    # not an E-type systematic — read dynamically so this works for any
    # parametrisation (HERAPDF, giuli, ...), not just the hardcoded HERAPDF set.
    initial_params: Dict[str, Dict] = {}
    for name, pdata in ref_params.items():
        if name in e_type_names:
            continue  # E-type nuisances are fixed via MINUIT index, not the Parameters block
        initial_params[name] = {'value': pdata['value'],
                                'step': max(abs(pdata['error']), 1e-4)}
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
    manifest: Dict = {'scan_1d': {}, 'scan_2d': {}}
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
                q2_cut=config.get('q2_cut', 3.5),
            )

            create_fit_structure(fit_dir, steering, "", config.datafiles,
                                 template_dir=template_dir, do_errors=do_errors,
                             xfitter_tree=config.xfitter_tree)

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
            # Warm-start E-type sources carrying an `init`, except the one being
            # scanned (its grid value is fixed via fix_commands above, and runs after).
            init_by_index = {
                e_type_indices[s['name']]: s['init']
                for s in systematics
                if s.get('type') == 'E' and s.get('init')
                and s['name'] in e_type_indices and s['name'] != name
            }
            _inject_init_commands(fit_dir / "config" / "parameters.yaml", init_by_index)
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

    # ── 2D contour scans ────────────────────────────────────────────────────
    scan_pairs = config.scan_params_2d
    if scan_pairs:
        sigma_levels = config.sigma_levels
        default_npoints_2d = int(defaults.get('npoints_2d', 21))
        default_n_sigma_2d = float(defaults.get('n_sigma_2d',
                                                int(np.ceil(max(sigma_levels))) + 1))

        def _resolve_axis(axis_name):
            """Return (kind, ref_value, ref_error, minuit_index) or None."""
            if axis_name not in ref_params:
                return None
            rv = ref_params[axis_name]['value']
            re_ = ref_params[axis_name]['error']
            if axis_name in e_type_indices:
                return ('E', rv, re_, e_type_indices[axis_name])
            return ('pdf', rv, re_, None)

        print(f"\n2D scan: {len(scan_pairs)} parameter pair(s)")
        print(f"Defaults: n_sigma_2d={default_n_sigma_2d}, npoints_2d={default_npoints_2d}, "
              f"sigma_levels={sigma_levels}")

        for pair_cfg in scan_pairs:
            xname, yname = pair_cfg['pair']
            npoints = int(pair_cfg.get('npoints', default_npoints_2d))
            n_sigma = float(pair_cfg.get('n_sigma', default_n_sigma_2d))

            ax, ay = _resolve_axis(xname), _resolve_axis(yname)
            if ax is None or ay is None:
                missing = [n for n, a in ((xname, ax), (yname, ay)) if a is None]
                print(f"  WARNING: pair ({xname}, {yname}) — {missing} not in reference "
                      f"fit params; skipping")
                continue
            for nm, a in ((xname, ax), (yname, ay)):
                if a[0] == 'E' and nm not in e_type_indices:
                    print(f"  WARNING: '{nm}' is E-type but has no MINUIT index; skipping pair")
                    a = None
            xkind, xref, xerr, xidx = ax
            ykind, yref, yerr, yidx = ay

            if 'x_range' in pair_cfg:
                xlo, xhi = (float(v) for v in pair_cfg['x_range'])
            else:
                xlo, xhi = xref - n_sigma * xerr, xref + n_sigma * xerr
            if 'y_range' in pair_cfg:
                ylo, yhi = (float(v) for v in pair_cfg['y_range'])
            else:
                ylo, yhi = yref - n_sigma * yerr, yref + n_sigma * yerr

            xs = np.linspace(xlo, xhi, npoints)
            ys = np.linspace(ylo, yhi, npoints)

            print(f"  [{xkind}x{ykind}] {xname} x {yname}: "
                  f"x[{xlo:.4g},{xhi:.4g}] y[{ylo:.4g},{yhi:.4g}] "
                  f"({npoints}x{npoints} = {npoints * npoints} fits)")

            if dry_run:
                total_fits += npoints * npoints
                continue

            fit_grid: List[List[str]] = []
            for i, xv in enumerate(xs):
                row = []
                for j, yv in enumerate(ys):
                    fit_name = f"2d_{xname}_{yname}_{i:03d}_{j:03d}"
                    fit_dir = fits_dir / fit_name

                    sources = [(s['name'], s['type'], s['epsilon']) for s in systematics]
                    steering = templates.render_steering(
                        sources=sources,
                        datafiles=config.datafiles,
                        n_iterations=config.get('n_iterations', 2),
                        enable_bartlett=config.get('enable_bartlett', True),
                        q2_cut=config.get('q2_cut', 3.5),
                    )
                    create_fit_structure(fit_dir, steering, "", config.datafiles,
                                         template_dir=template_dir, do_errors=do_errors,
                             xfitter_tree=config.xfitter_tree)

                    pdf_fixed: Dict[str, float] = {}
                    fix_cmds: Dict[str, Tuple[int, float]] = {}
                    if xkind == 'pdf':
                        pdf_fixed[xname] = xv
                    else:
                        fix_cmds[xname] = (xidx, xv)
                    if ykind == 'pdf':
                        pdf_fixed[yname] = yv
                    else:
                        fix_cmds[yname] = (yidx, yv)

                    _patch_parameters(
                        fit_dir / "config" / "parameters.yaml",
                        pdf_params=initial_params,
                        scan_fixed_params=pdf_fixed,
                        fix_commands=fix_cmds,
                    )
                    row.append(fit_name)
                    if not (fit_dir / "output" / "Results.txt").exists():
                        all_fit_dirs.append(fit_dir.resolve())
                fit_grid.append(row)

            manifest['scan_2d'][f"{xname}__{yname}"] = {
                'x_name': xname, 'y_name': yname,
                'x_values': xs.tolist(), 'y_values': ys.tolist(),
                'x_ref': xref, 'y_ref': yref, 'x_err': xerr, 'y_err': yerr,
                'n_sigma': n_sigma, 'npoints': npoints,
                'sigma_levels': sigma_levels,
                'fit_grid': fit_grid,
            }
            total_fits += npoints * npoints

    if dry_run:
        print(f"\n[DRY RUN] Would generate {total_fits} fits total")
        return None

    # Write manifest for result collection
    fits_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = fits_dir / "scan_manifest.json"
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)

    # Generate single-cluster batch submission
    submit_script = generate_batch_submit(
        fits_dir, all_fit_dirs, config.xfitter_tree,
        request_memory=str(config.get('request_memory', '2GB')),
    )

    print(f"\nCreated {total_fits} fits in {fits_dir}")
    print(f"Scan manifest: {manifest_file}")

    return submit_script
