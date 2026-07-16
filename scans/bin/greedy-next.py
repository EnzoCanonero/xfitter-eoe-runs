#!/usr/bin/env python3
"""
greedy-next command

Reads a finished systematic-ranking round, ranks the candidates by the
Bartlett-corrected dchi2, and writes the next round's study directory with the
winner promoted into `base_systematics` (warm-started at its converged shift).

Run from a finished round directory (one that has results/rankings.csv, i.e.
`plot` has been run):

    cd scans/studies/syst-ranking/hera-baseline/baseline
    ../../../../bin/greedy-next --threshold 2.2 --out ../2nd-1053

Why the corrected dchi2: the Bartlett-corrected chi2 is the statistic that
follows a chi2 distribution, so it is the endpoint the selection must compare.
Note the correction is NOT a common offset -- each candidate's own
gof_contrib (3 eps^2 - b_mutheta) enters it, which both shifts and re-orders
the ranking relative to the raw dchi2.

The stopping threshold must be calibrated, not assumed: a source that improves
the raw fit by nothing still scores dchi2_corrected ~ +1.2 (its free
Bartlett boost), so the old `> 1` rule would select everything. Use --report to
inspect the null bulk of a round before choosing.
"""

import argparse
import sys
from pathlib import Path

scans_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(scans_dir))

import pandas as pd

from lib.config import load_study_config


def _shift_of(round_dir: Path, systematic: str):
    """Converged shift of `systematic` in its own fit -- the warm-start value."""
    rankings = pd.read_csv(round_dir / "results" / "rankings.csv")
    row = rankings[rankings["systematic"] == systematic]
    if row.empty or pd.isna(row.iloc[0].get("shift")):
        return None
    return float(row.iloc[0]["shift"])


def _fmt_base_block(entries):
    lines = ["base_systematics:"]
    for name, init in entries:
        if init is None:
            lines.append(f"  - {{name: {name}, type: E}}")
        else:
            lines.append(f"  - {{name: {name}, type: E, init: {init:.4f}}}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--threshold", type=float, default=None,
                    help="stop if the best dchi2_corrected is below this "
                         "(calibrate it; see --report)")
    ap.add_argument("--out", type=Path, default=None,
                    help="directory for the next round (omit to only report)")
    ap.add_argument("--report", action="store_true",
                    help="only print the ranking and the null bulk")
    ap.add_argument("--top", type=int, default=10, help="rows to print")
    args = ap.parse_args()

    round_dir = Path.cwd()
    rankings_file = round_dir / "results" / "rankings.csv"
    if not rankings_file.exists():
        print(f"Error: {rankings_file} not found -- run `plot` in this round first.")
        sys.exit(1)

    cfg = load_study_config(round_dir)
    df = pd.read_csv(rankings_file)
    df = df[df["systematic"] != "nominal"].dropna(subset=["dchi2_corrected"])
    if df.empty:
        print("Error: no candidates with a dchi2_corrected value.")
        sys.exit(1)
    df = df.sort_values("dchi2_corrected", ascending=False).reset_index(drop=True)

    print(f"\nRound: {round_dir.name}   candidates: {len(df)}")
    print(f"\nTop {args.top} by Bartlett-corrected dchi2:")
    cols = ["systematic", "chi2", "chi2_corrected", "dchi2_corrected", "shift", "gof_contrib"]
    print(df[[c for c in cols if c in df.columns]].head(args.top).to_string(index=False))

    # The null bulk: most of ~170 candidates do nothing, so their dchi2_corrected
    # is just the free Bartlett boost. Any sane threshold sits above it.
    med = df["dchi2_corrected"].median()
    q90 = df["dchi2_corrected"].quantile(0.90)
    q99 = df["dchi2_corrected"].quantile(0.99)
    print(f"\nNull bulk of dchi2_corrected: median {med:.2f}, "
          f"90th pct {q90:.2f}, 99th pct {q99:.2f}")
    print("(a source with no real effect still scores ~ +1.2 -- the free boost)")

    best = df.iloc[0]
    winner, best_d = best["systematic"], float(best["dchi2_corrected"])
    runner_up = float(df.iloc[1]["dchi2_corrected"]) if len(df) > 1 else float("nan")
    print(f"\nBest: {winner}  dchi2_corrected = {best_d:.2f}  "
          f"(margin over next: {best_d - runner_up:+.2f})")

    if args.threshold is not None and best_d < args.threshold:
        print(f"\nSTOP: {best_d:.2f} < threshold {args.threshold} -- "
              f"the chain terminates at this round's base.")
        return
    if args.report or args.out is None:
        return

    # --- write the next round -------------------------------------------------
    base = [(e["name"], e.get("init")) for e in (cfg.data.get("base_systematics") or [])]
    base.append((winner, _shift_of(round_dir, winner)))

    text = (round_dir / "config.yaml").read_text()
    lines = [l for l in text.splitlines()
             if not l.startswith("base_systematics:")
             and not (l.startswith("  - {name:") and "type: E, init:" in l)]
    # drop any existing base_systematics block, then re-emit it before `datafiles:`
    out_lines, injected = [], False
    for l in lines:
        if l.startswith("datafiles:") and not injected:
            out_lines.append(_fmt_base_block(base))
            out_lines.append("")
            injected = True
        out_lines.append(l)
    if not injected:
        out_lines.append(_fmt_base_block(base))

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "config.yaml").write_text("\n".join(out_lines) + "\n")
    for link in ("run-scan", "plot"):
        dst = args.out / link
        if not dst.exists():
            rel = Path("../" * (len(args.out.resolve().relative_to(scans_dir.parent).parts) - 1))
            dst.symlink_to(scans_dir / "bin" / link)
    print(f"\nWrote {args.out/'config.yaml'} with base:")
    for name, init in base:
        print(f"  {name:16s} init={init if init is None else f'{init:.4f}'}")
    print(f"\nNext: cd {args.out} && ./run-scan")


if __name__ == "__main__":
    main()
