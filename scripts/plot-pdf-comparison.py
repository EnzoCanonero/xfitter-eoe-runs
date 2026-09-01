#!/usr/bin/env python3
"""Plot a PDF-comparison study from an explicitly named directory."""

import argparse
import sys
from pathlib import Path

# Allow this source-tree command to run without installing the package.
src_dir = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_dir))

from xfitter_eoe_runs.comparisons.pdf_compare import compare_pdfs


def main():
    parser = argparse.ArgumentParser(
        description="Write PDF-comparison plots for a configured study."
    )
    parser.add_argument(
        "study_dir",
        type=Path,
        help="comparison study directory containing config.yaml",
    )
    args = parser.parse_args()

    study_dir = args.study_dir.expanduser().resolve()
    config_file = study_dir / "config.yaml"

    if not config_file.is_file():
        parser.error(f"no config.yaml found in study directory: {study_dir}")

    try:
        compare_pdfs(study_dir)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
