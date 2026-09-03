"""Extract results and generate plots for a scan workspace."""

import argparse
import sys
from pathlib import Path

from ._paths import repository_root


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract results and generate plots for a scan workspace"
    )
    parser.add_argument(
        "run_dir",
        type=Path,
        help="scan workspace under runs/scans containing config.yaml",
    )
    args = parser.parse_args()

    try:
        repo_root = repository_root()
    except RuntimeError as error:
        parser.error(str(error))

    run_root = repo_root / "runs" / "scans"
    template_root = repo_root / "templates"
    run_dir = args.run_dir.expanduser().resolve()
    config_file = run_dir / "config.yaml"

    if not config_file.exists():
        print(f"Error: No config.yaml found in scan workspace: {run_dir}")
        sys.exit(1)

    try:
        run_dir.relative_to(run_root)
    except ValueError:
        parser.error(f"scan workspace must be under {run_root}: {run_dir}")

    fits_dir = run_dir / "runs"
    if not fits_dir.exists():
        print(f"Error: No runs/ directory found in {run_dir}")
        print("\nRun 'run-scan' first to generate runs.")
        sys.exit(1)

    try:
        from ..scans.plotter import plot_scan

        plot_scan(run_dir, template_root=template_root)
    except Exception as error:
        print(f"Error: {error}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
