#!/usr/bin/env python3
"""
plot-scan command
Extracts results and generates plots for a scan workspace
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from xfitter_eoe_runs.scans.plotter import plot_scan


RUN_ROOT = REPO_ROOT / "runs" / "scans"
TEMPLATE_ROOT = REPO_ROOT / "templates"


def main():
    parser = argparse.ArgumentParser(
        description="Extract results and generate plots for a scan workspace"
    )
    parser.add_argument(
        'run_dir',
        type=Path,
        help="scan workspace under runs/scans containing config.yaml",
    )
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    config_file = run_dir / "config.yaml"

    if not config_file.exists():
        print(f"Error: No config.yaml found in scan workspace: {run_dir}")
        sys.exit(1)

    try:
        run_dir.relative_to(RUN_ROOT)
    except ValueError:
        parser.error(f"scan workspace must be under {RUN_ROOT}: {run_dir}")

    # Check that the runtime fit directory exists
    fits_dir = run_dir / "runs"
    if not fits_dir.exists():
        print(f"Error: No runs/ directory found in {run_dir}")
        print("\nRun 'run-scan' first to generate runs.")
        sys.exit(1)

    try:
        plot_scan(run_dir, template_root=TEMPLATE_ROOT)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
