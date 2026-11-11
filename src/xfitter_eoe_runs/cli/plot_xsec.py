"""Plot a configured cross-section comparison workspace."""

import argparse
import sys
from pathlib import Path

from ._paths import repository_root


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write cross-section plots for a configured run workspace."
    )
    parser.add_argument(
        "run_dir",
        type=Path,
        help="comparison workspace under runs/comparisons containing config.yaml",
    )
    args = parser.parse_args()

    try:
        repo_root = repository_root()
    except RuntimeError as error:
        parser.error(str(error))

    run_root = repo_root / "runs" / "comparisons"
    run_dir = args.run_dir.expanduser().resolve()
    config_file = run_dir / "config.yaml"

    if not config_file.is_file():
        parser.error(f"no config.yaml found in comparison workspace: {run_dir}")

    try:
        run_dir.relative_to(run_root)
    except ValueError:
        parser.error(f"comparison workspace must be under {run_root}: {run_dir}")

    try:
        from ..comparisons.xsec_draw import compare_xsec

        compare_xsec(run_dir)
    except Exception as error:
        print(f"Error: {error}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
