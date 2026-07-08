#!/usr/bin/env python3
"""
plot command (PDF comparison)
Reads config.yaml in the current study directory and writes plots/pdf_comparison.pdf.
"""

import sys
from pathlib import Path

# Add fits/compare/ to the Python path so we can import the lib package.
# Use .resolve() so it works through symlinks (studies symlink this command).
compare_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(compare_dir))

from lib.pdf_compare import compare_pdfs


def main():
    study_dir = Path.cwd()
    config_file = study_dir / "config.yaml"

    if not config_file.exists():
        print(f"Error: No config.yaml found in current directory: {study_dir}")
        print("\nThis command must be run from within a comparison study directory.")
        print("Example: cd fits/compare/studies/my-comparison && plot")
        sys.exit(1)

    try:
        compare_pdfs(study_dir)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
