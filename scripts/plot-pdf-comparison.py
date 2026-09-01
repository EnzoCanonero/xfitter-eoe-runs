#!/usr/bin/env python3
"""Plot a PDF comparison from an explicitly named run workspace."""

import argparse
import sys
from pathlib import Path

# Allow this source-tree command to run without installing the package.
src_dir = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_dir))

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_ROOT = REPO_ROOT / "runs" / "comparisons"

from xfitter_eoe_runs.comparisons.pdf_compare import compare_pdfs


def main():
    parser = argparse.ArgumentParser(
        description="Write PDF-comparison plots for a configured run workspace."
    )
    parser.add_argument(
        "run_dir",
        type=Path,
        help="comparison workspace under runs/comparisons containing config.yaml",
    )
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    config_file = run_dir / "config.yaml"

    if not config_file.is_file():
        parser.error(f"no config.yaml found in comparison workspace: {run_dir}")

    try:
        run_dir.relative_to(RUN_ROOT)
    except ValueError:
        parser.error(f"comparison workspace must be under {RUN_ROOT}: {run_dir}")

    try:
        compare_pdfs(run_dir)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
