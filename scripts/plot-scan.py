#!/usr/bin/env python3
"""
plot-scan command
Extracts results and generates plots for a scan study
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from xfitter_eoe_runs.scans.plotter import plot_scan


TEMPLATE_ROOT = REPO_ROOT / "scans" / "templates"


def main():
    parser = argparse.ArgumentParser(
        description="Extract results and generate plots for a scan study"
    )
    parser.add_argument(
        'study_dir',
        type=Path,
        help="Study directory containing config.yaml",
    )
    args = parser.parse_args()

    study_dir = args.study_dir.expanduser().resolve()
    config_file = study_dir / "config.yaml"

    if not config_file.exists():
        print(f"Error: No config.yaml found in study directory: {study_dir}")
        sys.exit(1)

    # Check that runs directory exists
    fits_dir = study_dir / "runs"
    if not fits_dir.exists():
        print(f"Error: No runs/ directory found in {study_dir}")
        print("\nRun 'run-scan' first to generate runs.")
        sys.exit(1)

    try:
        plot_scan(study_dir, template_root=TEMPLATE_ROOT)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
