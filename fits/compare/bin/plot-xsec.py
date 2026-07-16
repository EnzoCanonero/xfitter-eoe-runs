#!/usr/bin/env python3
"""
plot-xsec command (cross-section comparison via xfitter-draw)
Reads config.yaml (type: xsec-comparison) in the current study directory and
writes plots/xsec_comparison.pdf. See lib/xsec_draw.py for the config schema.
"""

import sys
from pathlib import Path

compare_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(compare_dir))

from lib.xsec_draw import compare_xsec


def main():
    study_dir = Path.cwd()
    if not (study_dir / "config.yaml").exists():
        print(f"Error: no config.yaml in {study_dir}")
        print("Run from a study directory, e.g. "
              "cd fits/compare/studies/my-xsec-study && ../../bin/plot-xsec")
        sys.exit(1)
    try:
        compare_xsec(study_dir)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
