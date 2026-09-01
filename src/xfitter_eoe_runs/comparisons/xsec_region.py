#!/usr/bin/env python3
"""
xsec-region-table: where in the (Q^2, x) plane two fits differ.

Bins the fitted data points in Q^2 and x and reports, per cell, the change in the
data term of the chi2 between a reference fit and a comparison fit,

    dchi2(cell) = sum_cell pull^2(fit) - sum_cell pull^2(reference)

together with the number of points in the cell, plus row and column totals.
A negative number means the comparison fit describes that region better.

IMPORTANT — what this does and does not account for
---------------------------------------------------
The per-point pulls in fittedresults.txt carry only the DATA term of the chi2:
each is (data - theory_shifted)/sigma_uncor for one measurement. The correlated
nuisance-parameter constraints and the prediction-dependent logarithmic term
are properties of the fit as a whole, not of any single point, so they cannot
be binned and are NOT in this table. The entries therefore do not add up to the
total chi2 difference. For the HERA 7-source EoE fit the split is data -57.7,
nuisance constraints +10.2 and prediction-dependent logarithmic term -3.1,
giving a net change of -50.5.

The pull column is theory-with-shifts based (theo_mod), i.e. the description the
fit actually achieves, which is what the chi2 minimises.

Config keys (runs/comparisons/<workspace>/config.yaml)
------------------------------------------------
type: xsec-region-table
q2bins: [0, 10, 30, 100, 1000, 1.0e9]     # bin EDGES, ascending
xbins:  [0, 1.0e-3, 1.0e-2, 1.0e-1, 1.0]  # bin EDGES, ascending
dataset: ""                                # optional substring filter; "" = all
fits:                                      # exactly 2; first = reference
  - {label: "nominal",  path: ../../fits/hera-baseline/nominal-bartlett2-pumplin}
  - {label: "EoE-7src", path: ../../fits/hera-baseline/baseline-7-sources-bartlett2-pumplin}
"""

import math
from pathlib import Path

from .xsec_draw import _is_data_row, _load_config


# ---------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------

def _read_points(fit_dir: Path, dataset: str):
    """Return [(dataset_label, q2, x, pull), ...] for one fit's fitted points."""
    out = fit_dir
    if (out / "output").is_dir():
        out = out / "output"
    fr = out / "fittedresults.txt"
    if not fr.is_file():
        raise FileNotFoundError(f"not found: {fr}")

    lines = fr.read_text().splitlines()
    points, label = [], ""
    for i, line in enumerate(lines):
        p = line.split()
        # a dataset block opens with its number, then its label on the next line
        if len(p) == 1 and p[0].isdigit() and len(p[0]) >= 5 and i + 1 < len(lines):
            label = lines[i + 1].strip()
            continue
        if not _is_data_row(line):
            continue
        if dataset and dataset not in label:
            continue
        # cols: q2 x y data uncor tot theo theo_mod therr+ therr- pull ...
        points.append((label, float(p[0]), float(p[1]),
                       float(p[10].replace("-.", "-0."))))
    return points


def _bin_index(value: float, edges):
    for k in range(len(edges) - 1):
        if edges[k] <= value < edges[k + 1]:
            return k
    return None


# ---------------------------------------------------------------------------
# formatting
# ---------------------------------------------------------------------------

def _fmt_edge(v: float) -> str:
    if v == 0:
        return "0"
    if v >= 1:
        return f"{v:g}"
    exponent = math.floor(math.log10(v))
    mantissa = v / 10**exponent
    if math.isclose(mantissa, 1.0, rel_tol=1e-10, abs_tol=1e-12):
        return f"10^{{{exponent}}}"
    return rf"{mantissa:g}\times10^{{{exponent}}}"


def _q2_label(lo, hi, last):
    if lo == 0:
        return rf"$Q^2 < {hi:g}$"
    if last:
        return rf"$Q^2 \geq {lo:g}$"
    return rf"${lo:g}\leq Q^2 < {hi:g}$"


def _x_label(lo, hi, last):
    if lo == 0:
        return rf"$x < {_fmt_edge(hi)}$"
    if last:
        return rf"$x \geq {_fmt_edge(lo)}$"
    return rf"${_fmt_edge(lo)}\leq x < {_fmt_edge(hi)}$"


def _validate_edges(name: str, edges):
    if len(edges) < 2 or any(b <= a for a, b in zip(edges, edges[1:])):
        raise ValueError(f"{name} must contain at least two strictly increasing edges")


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def region_table(run_dir: Path):
    run_dir = Path(run_dir)
    cfg = _load_config(run_dir / "config.yaml")
    if cfg.get("type") != "xsec-region-table":
        raise ValueError(f"config type is '{cfg.get('type')}', expected 'xsec-region-table'")

    fits = cfg.get("fits") or []
    if len(fits) != 2:
        raise ValueError(f"xsec-region-table needs exactly 2 fits (reference first), got {len(fits)}")

    q2e = [float(v) for v in (cfg.get("q2bins") or [0, 10, 30, 100, 1000, 1.0e9])]
    xe = [float(v) for v in (cfg.get("xbins") or [0, 1.0e-3, 1.0e-2, 1.0e-1, 1.0])]
    _validate_edges("q2bins", q2e)
    _validate_edges("xbins", xe)
    dataset = cfg.get("dataset") or ""

    ref_entry, cmp_entry = fits
    ref_pts = _read_points((run_dir / ref_entry["path"]).resolve(), dataset)
    cmp_pts = _read_points((run_dir / cmp_entry["path"]).resolve(), dataset)

    if len(ref_pts) != len(cmp_pts):
        raise RuntimeError(f"grid mismatch: {len(ref_pts)} vs {len(cmp_pts)} points")
    for (l1, q1, x1, _), (l2, q2, x2, _) in zip(ref_pts, cmp_pts):
        if l1 != l2 or abs(q1 - q2) > 1e-9 or abs(x1 - x2) > 1e-12:
            raise RuntimeError(f"grid mismatch at ({l1}, {q1}, {x1}) vs ({l2}, {q2}, {x2})")

    print(f"  reference : {ref_entry['label']}  ({len(ref_pts)} points)")
    print(f"  comparison: {cmp_entry['label']}")
    if dataset:
        print(f"  dataset filter: '{dataset}'")

    nq, nx = len(q2e) - 1, len(xe) - 1
    d = [[0.0] * nx for _ in range(nq)]
    n = [[0] * nx for _ in range(nq)]
    skipped = 0
    for (_, q2, x, pr), (_, _, _, pc) in zip(ref_pts, cmp_pts):
        i, j = _bin_index(q2, q2e), _bin_index(x, xe)
        if i is None or j is None:
            skipped += 1
            continue
        d[i][j] += pc * pc - pr * pr
        n[i][j] += 1
    if skipped:
        print(f"  WARNING: {skipped} point(s) fell outside the bin edges")

    total = sum(sum(r) for r in d)
    npts = sum(sum(r) for r in n)
    col_tot = [sum(d[i][j] for i in range(nq)) for j in range(nx)]
    row_tot = [sum(d[i]) for i in range(nq)]

    results_dir = run_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # ---- csv ----
    csv = ["q2_lo,q2_hi,x_lo,x_hi,npoints,dchi2"]
    for i in range(nq):
        for j in range(nx):
            csv.append(f"{q2e[i]:g},{q2e[i+1]:g},{xe[j]:g},{xe[j+1]:g},{n[i][j]},{d[i][j]:.4f}")
    (results_dir / "region_table.csv").write_text("\n".join(csv) + "\n")

    # ---- latex ----
    cols = "l" + "r" * nx + "|r"
    L = [r"\begin{tabular}{" + cols + "}", r"\hline"]
    hdr = [""] + [_x_label(xe[j], xe[j + 1], j == nx - 1) for j in range(nx)] + [r"total"]
    L.append(" & ".join(hdr) + r" \\")
    L.append(r"\hline")
    for i in range(nq):
        row = [_q2_label(q2e[i], q2e[i + 1], i == nq - 1)]
        for j in range(nx):
            row.append(f"${d[i][j]:+.1f}$ ({n[i][j]})" if n[i][j] else "--")
        row.append(f"${row_tot[i]:+.1f}$")
        L.append(" & ".join(row) + r" \\")
    L.append(r"\hline")
    L.append(" & ".join([r"total"] + [f"${c:+.1f}$" for c in col_tot]
                        + [f"${total:+.1f}$"]) + r" \\")
    L.append(r"\hline")
    L.append(r"\end{tabular}")
    (results_dir / "region_table.tex").write_text("\n".join(L) + "\n")

    # ---- console ----
    w = 24
    print(f"\n  dchi2 = chi2_data({cmp_entry['label']}) - chi2_data({ref_entry['label']}), "
          f"per (Q^2, x) cell, with (npoints)\n")
    corner = "Q2 \\ x"
    head = f"  {corner:<24}" + "".join(
        f"{_x_label(xe[j], xe[j+1], j == nx-1).replace('$',''):>{w}}" for j in range(nx))
    print(head + f"{'row tot':>12}")
    for i in range(nq):
        lbl = _q2_label(q2e[i], q2e[i + 1], i == nq - 1).replace("$", "")
        line = f"  {lbl:<24}"
        for j in range(nx):
            line += f"{(f'{d[i][j]:+.1f} ({n[i][j]})' if n[i][j] else '-'):>{w}}"
        print(line + f"{row_tot[i]:+12.1f}")
    line = f"  {'col tot':<24}" + "".join(f"{col_tot[j]:+{w}.1f}" for j in range(nx))
    print(line + f"{total:+12.1f}")
    print(f"\n  total dchi2 (data term) = {total:+.2f} over {npts} points")
    print("  NB: the nuisance constraints and prediction-dependent logarithmic "
          "term are not per-point and are excluded.")
    print(f"\nWrote {results_dir/'region_table.tex'}\n      {results_dir/'region_table.csv'}")
    return results_dir / "region_table.tex"
