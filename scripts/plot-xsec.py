#!/usr/bin/env python3
"""Plot a cross-section study from an explicitly named directory.

Dispatches on the study config's ``type``:
  xsec-comparison   -> plots/xsec_comparison.pdf
  xsec-region-table -> results/region_table.{tex,csv}
"""

import argparse
import sys
from pathlib import Path

# Allow this source-tree command to run without installing the package.
src_dir = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_dir))

from xfitter_eoe_runs.comparisons.xsec_draw import compare_xsec, _load_config
from xfitter_eoe_runs.comparisons.xsec_region import region_table

HANDLERS = {
    "xsec-comparison": compare_xsec,
    "xsec-region-table": region_table,
}


def main():
    parser = argparse.ArgumentParser(
        description="Write cross-section plots or tables for a configured study."
    )
    parser.add_argument(
        "study_dir",
        type=Path,
        help="comparison study directory containing config.yaml",
    )
    args = parser.parse_args()

    study_dir = args.study_dir.expanduser().resolve()
    if not (study_dir / "config.yaml").is_file():
        parser.error(f"no config.yaml found in study directory: {study_dir}")
    try:
        stype = _load_config(study_dir / "config.yaml").get("type")
        handler = HANDLERS.get(stype)
        if handler is None:
            print(f"Error: config type '{stype}' is not handled by plot-xsec "
                  f"(expected one of: {', '.join(HANDLERS)})")
            sys.exit(1)
        handler(study_dir)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
