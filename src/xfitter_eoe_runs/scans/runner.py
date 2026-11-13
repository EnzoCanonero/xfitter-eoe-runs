"""
Scan runner implementation
Generates fits and submits to Condor based on a workspace config
"""

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import yaml
from .config import (load_study_config, LambdaScanConfig, LikelihoodScanConfig,
                     SystematicRankingConfig, PumplinStabilityConfig)
from .templates import (TemplateManager, create_fit_structure,
                         generate_batch_submit)


def _set_pdf_parameter(parameters: Dict, name: str, values: Dict) -> None:
    """Update a numeric parameter without dropping its bounds."""
    entry = parameters.get(name)
    if not values or set(values) - {'value', 'step'}:
        raise ValueError(f"{name}: expected value and/or step")
    for key, value in values.items():
        value = float(value)
        if not np.isfinite(value) or (key == 'step' and value < 0):
            raise ValueError(f"{name}: invalid {key}")
        if isinstance(entry, list) and len(entry) >= 2:
            entry[0 if key == 'value' else 1] = value
        elif isinstance(entry, dict) and 'value' in entry and 'step' in entry:
            entry[key] = value
        else:
            raise ValueError(f"{name}: expected a numeric parameter with value and step")


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
    without fixing the parameter. Zero/None values are
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

    Source indices follow the parameter and source declarations.
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


def run_scan(run_dir: Path, template_root: Path, dataset_root: Optional[Path],
             setup_env: Path, dry_run: bool = False, submit: bool = True):
    """
    Generate fits for a scan workspace and optionally submit to Condor

    Args:
        run_dir: Path to the workspace containing config.yaml and runtime output
        template_root: Path containing the named scan templates
        dataset_root: Explicit dataset directory override; None uses config.yaml
        setup_env: Environment setup script to source in generated jobs
        dry_run: If True, only print what would be done without creating files
        submit: If True, automatically submit jobs to Condor after generating fits
    """
    # Load configuration
    run_dir = Path(run_dir)
    config = load_study_config(run_dir, template_root)
    dataset_root = (config.dataset_root if dataset_root is None
                    else Path(dataset_root).expanduser().resolve())
    if not dataset_root.is_dir():
        raise FileNotFoundError(f"dataset_root directory not found: {dataset_root}")

    print(f"Scan type: {config.scan_type}")
    print(f"Run workspace: {run_dir}")
    print(f"Dataset root: {dataset_root}")

    if config.do_errors:
        print(f"doErrors: {config.do_errors['method']}")

    # Create runs directory
    fits_dir = run_dir / "runs"

    if config.scan_type == 'lambda-scan':
        submit_script = _generate_lambda_scan_fits(
            config, fits_dir, dry_run, dataset_root, setup_env
        )
    elif config.scan_type == 'systematic-ranking':
        submit_script = _generate_systematic_ranking_fits(
            config, fits_dir, dry_run, dataset_root, setup_env
        )
    elif config.scan_type == 'pumplin-stability':
        submit_script = _generate_pumplin_stability_fits(
            config, fits_dir, dry_run, dataset_root, setup_env
        )
    elif config.scan_type == 'likelihood-scan':
        submit_script = _generate_likelihood_scan_fits(
            config, fits_dir, dry_run, dataset_root, setup_env
        )
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


def _generate_pumplin_stability_fits(config: PumplinStabilityConfig,
                                     fits_dir: Path, dry_run: bool,
                                     dataset_root: Path, setup_env: Path):
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
                                     template_dir=template_dir,
                                     dataset_root=dataset_root,
                                     setup_env=setup_env,
                                     do_errors=do_errors,
                                     xfitter_tree=config.xfitter_tree,
                                     xfitter_commit=config.xfitter_commit)
                _apply_source_inits(fit_dir, syslist)
                all_fit_dirs.append(fit_dir.resolve())

    print(f"\nCreated {len(all_fit_dirs)} fits in {fits_dir}")
    return generate_batch_submit(
        fits_dir, all_fit_dirs, setup_env=setup_env,
        xfitter_tree=config.xfitter_tree,
        xfitter_commit=config.xfitter_commit,
        request_memory=str(config.get('request_memory', '2GB')),
    )


def _generate_lambda_scan_fits(config: LambdaScanConfig, fits_dir: Path,
                               dry_run: bool, dataset_root: Path,
                               setup_env: Path):
    """Generate fits for lambda-scan"""

    # Template folder selected by the scan config's `template:` field
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
                             template_dir=template_dir,
                             dataset_root=dataset_root,
                             setup_env=setup_env, do_errors=do_errors,
                             xfitter_tree=config.xfitter_tree,
                             xfitter_commit=config.xfitter_commit)
        _apply_source_inits(fit_dir, systematics)
        all_fit_dirs.append(fit_dir.resolve())

    print(f"\nCreated {len(lambda_vals)} fits in {fits_dir}")
    return generate_batch_submit(
        fits_dir, all_fit_dirs, setup_env=setup_env,
        xfitter_tree=config.xfitter_tree,
        xfitter_commit=config.xfitter_commit,
        request_memory=str(config.get('request_memory', '2GB')),
    )


def _generate_systematic_ranking_fits(config: SystematicRankingConfig,
                                      fits_dir: Path, dry_run: bool,
                                      dataset_root: Path, setup_env: Path):
    """Generate fits for systematic-ranking"""

    # Template folder selected by the scan config's `template:` field
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
                         template_dir=template_dir,
                         dataset_root=dataset_root, setup_env=setup_env,
                         do_errors=do_errors, xfitter_tree=config.xfitter_tree,
                         xfitter_commit=config.xfitter_commit)
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
                             template_dir=template_dir,
                             dataset_root=dataset_root, setup_env=setup_env,
                             do_errors=do_errors,
                             xfitter_tree=config.xfitter_tree,
                             xfitter_commit=config.xfitter_commit)
        _apply_source_inits(fit_dir, fit_systematics)
        all_fit_dirs.append(fit_dir.resolve())

    print(f"\nCreated {len(systematics) + 1} fits in {fits_dir} (including nominal)")
    return generate_batch_submit(
        fits_dir, all_fit_dirs, setup_env=setup_env,
        xfitter_tree=config.xfitter_tree,
        xfitter_commit=config.xfitter_commit,
        request_memory=str(config.get('request_memory', '2GB')),
    )


def _generate_likelihood_scan_fits(config: LikelihoodScanConfig,
                                   fits_dir: Path, dry_run: bool,
                                   dataset_root: Path, setup_env: Path):
    """Generate the nominal fit and manual 1D/2D grids together."""
    templates = TemplateManager(config.template_dir)
    parameters_text = templates.render_parameters(fits_dir, config.do_errors_string)
    block = re.search(r'^Parameters:[ \t]*\n.*?(?=^\S|\Z)',
                      parameters_text, re.MULTILINE | re.DOTALL)
    if block is None:
        raise ValueError("template is missing its Parameters block")
    parameters = yaml.safe_load(block.group())['Parameters']
    for name, values in config.parameter_overrides.items():
        _set_pdf_parameter(parameters, name, values)

    systematics = config.systematics
    e_names = [s['name'] for s in systematics if s['type'] == 'E']
    if len(set(e_names)) != len(e_names) or set(e_names) & parameters.keys():
        raise ValueError("E-source names must be unique and distinct from PDF parameters")
    e_indices = {name: len(parameters) + i + 1 for i, name in enumerate(e_names)}
    if e_names and '    call fcn 1\n' not in parameters_text:
        raise ValueError("template Commands must contain 'call fcn 1'")
    steering = templates.render_steering(
        sources=[(s['name'], s['type'], s['epsilon']) for s in systematics],
        datafiles=config.datafiles,
        n_iterations=config.get('n_iterations', 2),
        enable_bartlett=config.get('enable_bartlett', True),
        q2_cut=config.get('q2_cut', 3.5),
    )

    def check_parameter(name):
        if name in e_indices:
            return
        entry = parameters.get(name)
        step = (entry.get('step', 0) if isinstance(entry, dict) else
                entry[1] if isinstance(entry, list) and len(entry) >= 2 else 0)
        if not np.isfinite(float(step)) or float(step) <= 0:
            raise ValueError(f"{name}: scan parameter must be free in the nominal fit")

    def grid(bounds, npoints):
        lo, hi = map(float, bounds)
        if not np.isfinite([lo, hi]).all() or lo >= hi:
            raise ValueError("scan bounds must be finite and increasing")
        if not isinstance(npoints, int) or isinstance(npoints, bool) or npoints < 2:
            raise ValueError("npoints must be an integer >= 2")
        return np.linspace(lo, hi, npoints).tolist()

    jobs = [('nominal', {})]
    manifest = {'nominal': 'nominal', 'scan_1d': {}, 'scan_2d': {}}
    for entries, is_systematic in ((config.scan_params_1d, False),
                                   (config.scan_systematics_1d, True)):
        for entry in entries:
            name = entry['name']
            check_parameter(name)
            if (name in e_indices) != is_systematic:
                raise ValueError(f"{name}: use the matching PDF or systematic scan list")
            if name in manifest['scan_1d']:
                raise ValueError(f"duplicate scan: {name}")
            values = grid((entry['min'], entry['max']), entry['npoints'])
            fit_names = []
            for i, value in enumerate(values):
                fit_name = f"1d_{name}_{i:03d}"
                jobs.append((fit_name, {name: value}))
                fit_names.append(fit_name)
            manifest['scan_1d'][name] = {'scan_values': values, 'fit_dirs': fit_names}
            print(f"  {name}: [{values[0]:g}, {values[-1]:g}], {len(values)} points")

    for entry in config.scan_params_2d:
        xname, yname = entry['pair']
        check_parameter(xname)
        check_parameter(yname)
        key = f"{xname}__{yname}"
        if xname == yname or key in manifest['scan_2d']:
            raise ValueError(f"duplicate scan axes or pair: {key}")
        nx, ny = entry['npoints']
        xs = grid(entry['x_range'], nx)
        ys = grid(entry['y_range'], ny)
        fit_grid = []
        for i, xv in enumerate(xs):
            row = []
            for j, yv in enumerate(ys):
                fit_name = f"2d_{xname}_{yname}_{i:03d}_{j:03d}"
                jobs.append((fit_name, {xname: xv, yname: yv}))
                row.append(fit_name)
            fit_grid.append(row)
        manifest['scan_2d'][key] = {
            'x_name': xname, 'y_name': yname,
            'x_values': xs, 'y_values': ys, 'fit_grid': fit_grid,
        }
        print(f"  {xname} x {yname}: {nx} x {ny} points")

    print(f"\nLikelihood scan: {len(jobs)} fits including nominal")
    if dry_run:
        return None
    if fits_dir.exists() and any(fits_dir.iterdir()):
        raise ValueError("likelihood runs/ already exists; generate in a fresh workspace")

    fit_dirs = []
    for fit_name, fixed in jobs:
        fit_dir = fits_dir / fit_name
        create_fit_structure(
            fit_dir, steering, "", config.datafiles,
            template_dir=config.template_dir, dataset_root=dataset_root,
            setup_env=setup_env, do_errors=config.do_errors_string,
            xfitter_tree=config.xfitter_tree, xfitter_commit=config.xfitter_commit,
        )
        fit_parameters = deepcopy(parameters)
        for name, value in fixed.items():
            if name not in e_indices:
                _set_pdf_parameter(fit_parameters, name, {'value': value, 'step': 0})
        replacement = yaml.safe_dump({'Parameters': fit_parameters},
                                    sort_keys=False, default_flow_style=None)
        text = parameters_text[:block.start()] + replacement + parameters_text[block.end():]
        commands = []
        for source in systematics:
            name = source['name']
            if name not in e_indices:
                continue
            value = fixed.get(name, source.get('init'))
            if value is not None:
                commands.append(f"    set par {e_indices[name]} {value:.16g}\n")
            if name in fixed:
                commands.append(f"    fix {e_indices[name]}\n")
        if commands:
            text = text.replace('    call fcn 1\n',
                                ''.join(commands) + '    call fcn 1\n', 1)
        (fit_dir / 'config/parameters.yaml').write_text(text)
        fit_dirs.append(fit_dir.resolve())

    (fits_dir / 'scan_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return generate_batch_submit(
        fits_dir, fit_dirs, setup_env=setup_env,
        xfitter_tree=config.xfitter_tree, xfitter_commit=config.xfitter_commit,
        request_memory=str(config.get('request_memory', '2GB')),
    )
