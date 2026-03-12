#!/usr/bin/env python3
"""
plot command
Extracts results and generates plots for a scan study
"""

import sys
from pathlib import Path

# Add scans/ to Python path so we can import lib package
# Use .resolve() to handle symlinks correctly
scans_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(scans_dir))

from lib.plotter import plot_scan


def main():
    # Detect current directory is a study directory (contains config.yaml)
    study_dir = Path.cwd()
    config_file = study_dir / "config.yaml"

    if not config_file.exists():
        print(f"Error: No config.yaml found in current directory: {study_dir}")
        print("\nThis command must be run from within a study directory.")
        print("Example: cd scans/studies/my-study && plot")
        sys.exit(1)

    # Check that runs directory exists
    fits_dir = study_dir / "runs"
    if not fits_dir.exists():
        print(f"Error: No runs/ directory found in {study_dir}")
        print("\nRun 'run-scan' first to generate runs.")
        sys.exit(1)

    try:
        plot_scan(study_dir)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
