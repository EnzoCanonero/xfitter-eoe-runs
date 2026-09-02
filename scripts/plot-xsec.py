#!/usr/bin/env python3
"""Plot a cross-section comparison from an explicitly named run workspace.

Dispatches on the workspace config's ``type``:
  xsec-comparison   -> plots/xsec_comparison.pdf
  xsec-region-table -> results/region_table.{tex,csv}
"""

import argparse
import sys
from pathlib import Path

# Allow this source-tree command to run without installing the package.
src_dir = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_dir))

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_ROOT = REPO_ROOT / "runs" / "comparisons"

from xfitter_eoe_runs.comparisons.xsec_draw import compare_xsec, _load_config
from xfitter_eoe_runs.comparisons.xsec_region import region_table

HANDLERS = {
    "xsec-comparison": compare_xsec,
    "xsec-region-table": region_table,
}


def main():
    parser = argparse.ArgumentParser(
        description="Write cross-section plots or tables for a configured run workspace."
    )
    parser.add_argument(
        "run_dir",
        type=Path,
        help="comparison workspace under runs/comparisons containing config.yaml",
    )
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    if not (run_dir / "config.yaml").is_file():
        parser.error(f"no config.yaml found in comparison workspace: {run_dir}")
    try:
        run_dir.relative_to(RUN_ROOT)
    except ValueError:
        parser.error(f"comparison workspace must be under {RUN_ROOT}: {run_dir}")
    try:
        stype = _load_config(run_dir / "config.yaml").get("type")
        handler = HANDLERS.get(stype)
        if handler is None:
            print(f"Error: config type '{stype}' is not handled by plot-xsec "
                  f"(expected one of: {', '.join(HANDLERS)})")
            sys.exit(1)
        handler(run_dir)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
