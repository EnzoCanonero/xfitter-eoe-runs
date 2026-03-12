"""
Scan runner implementation
Generates fits and submits to Condor based on study config
"""

from pathlib import Path
from typing import List, Tuple
import numpy as np
from .config import load_study_config, LambdaScanConfig, SystematicRankingConfig
from .templates import TemplateManager, create_fit_structure, generate_condor_wrapper


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
    else:
        raise ValueError(f"Unknown scan type: {config.scan_type}")

    if not dry_run:
        # Generate master Condor submission wrapper
        wrapper = generate_condor_wrapper(fits_dir)
        print(f"\nMaster submission script: {wrapper}")

        # Automatically submit jobs if requested
        if submit:
            import subprocess
            print("\nSubmitting all fits to Condor...")
            try:
                result = subprocess.run(
                    ['bash', str(wrapper)],
                    cwd=fits_dir,
                    capture_output=True,
                    text=True,
                    check=True
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
    else:
        print("\n[DRY RUN] No files were created")


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


def _generate_systematic_ranking_fits(config: SystematicRankingConfig, fits_dir: Path, dry_run: bool):
    """Generate fits for systematic-ranking"""

    # Get template manager
    template_dir = Path(__file__).parent.parent / "templates"
    templates = TemplateManager(template_dir)

    systematics = config.systematics

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

    print(f"\nCreated {len(systematics) + 1} fits in {fits_dir} (including nominal)")
