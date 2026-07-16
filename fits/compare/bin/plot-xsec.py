#!/usr/bin/env python3
"""
plot-xsec command (cross-section studies)

Reads config.yaml in the current study directory and dispatches on `type`:
  xsec-comparison   -> plots/xsec_comparison.pdf   (see lib/xsec_draw.py)
  xsec-region-table -> results/region_table.{tex,csv}  (see lib/xsec_region.py)
"""

import sys
from pathlib import Path

compare_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(compare_dir))

from lib.xsec_draw import compare_xsec, _load_config
from lib.xsec_region import region_table

HANDLERS = {
    "xsec-comparison": compare_xsec,
    "xsec-region-table": region_table,
}


def main():
    study_dir = Path.cwd()
    if not (study_dir / "config.yaml").exists():
        print(f"Error: no config.yaml in {study_dir}")
        print("Run from a study directory, e.g. "
              "cd fits/compare/studies/my-xsec-study && ../../bin/plot-xsec")
        sys.exit(1)
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
