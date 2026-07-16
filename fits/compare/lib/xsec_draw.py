#!/usr/bin/env python3
"""
xsec-comparison pipeline: Fig.2-style reduced-cross-section overlays of N fits,
rendered by the REAL xfitter-draw (logo, hatched therr bands, delta-total band,
Theory+shifts, ratio panel), driven by a study config.yaml.

How it works
------------
xfitter-draw natively overlays several output directories, but always draws
every dataset and every Q2 subplot. This pipeline gets panel selection by
STAGING: for each fit it writes a temporary directory containing a FILTERED
fittedresults.txt (only the requested dataset and Q2 bins; header and Plot
metadata kept verbatim, so panel titles/axes are untouched) plus symlinks to
Results.txt / minuit.out.txt / parsout_0 so the chi2 and parameter table pages
reflect the full fits. xfitter-draw then draws exactly the requested panels.

Theory error bands (--therr) come from the therr+/- columns, which are filled
(and Bartlett-scaled) by fits run with the bartlett-fixes binary from
2026-07-13 onwards; older outputs have zeros there and simply show no band.

Config keys (studies/<name>/config.yaml)
----------------------------------------
type: xsec-comparison
dataset: "HERA1+2 NCep 920"        # substring match on the dataset label
q2bins: [3.5, 4.5, 6.5, 8.5]       # Q2 values to draw; omit/empty = all bins
fits:                               # 2+ entries; first = reference/data holder
  - {label: "nominal",  path: ../../../hera-baseline/nominal-bartlett2-hesse}
  - {label: "EoE-7src", path: ../../../hera-baseline/baseline-7-sources-bartlett2-hesse}

# element toggles (defaults reproduce the Fig.2 / xfitter-draw look)
therr: true                # theory uncertainty bands        (--therr)
shifts: true               # dashed Theory+shifts curves     (off -> --nothshifts)
uncorr_ticks: true         # delta-uncorrelated inner ticks  (off -> --nouncorrerr)
logo: true                 # xFitter logo                    (off -> --no-logo)
upband: true               # band in the upper (sigma) panel (off -> --noupband)

# layout / style knobs
ratio_to_theory: false     # ratio panel relative to theory  (--ratio-to-theory)
ratiorange: null           # "0.9:1.1"                       (--ratiorange)
xrange: null               # "5e-5:0.02"                     (--xrange)
plots_per_page: null       # panels per page, default 4      (--plots-per-page)
filledbands: false         # filled instead of hatched bands (--filledbands)
transparentbands: false    #                                 (--transparentbands)
extra_options: []          # raw passthrough, e.g. ["--thicklines", "--bw"]

xfitter_tree: xfitter-bartlett-fixes   # binary tree under $XFITTER_ROOT
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


# ---------------------------------------------------------------------------
# Minimal config parser fallback (the xfitter env's python has no PyYAML).
# Supports exactly the documented schema: comments, `key: scalar`,
# `key: [a, b, ...]`, and a `fits:` block of `- {k: v, k: v}` lines.
# ---------------------------------------------------------------------------

def _scalar(tok: str):
    tok = tok.strip()
    if tok in ("", "~", "null", "None"):
        return None
    if tok in ("true", "True"):
        return True
    if tok in ("false", "False"):
        return False
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in "'\"":
        return tok[1:-1]
    try:
        return int(tok)
    except ValueError:
        pass
    try:
        return float(tok)
    except ValueError:
        pass
    return tok


def _strip_comment(line: str) -> str:
    out, quote = [], None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _mini_yaml(text: str) -> dict:
    cfg, key_for_list = {}, None
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        s = line.strip()
        if s.startswith("- {") and s.endswith("}") and key_for_list:
            item = {}
            for part in s[3:-1].split(","):
                if ":" in part:
                    k, v = part.split(":", 1)
                    item[k.strip()] = _scalar(v)
            cfg.setdefault(key_for_list, []).append(item)
            continue
        if ":" in s:
            k, v = s.split(":", 1)
            k, v = k.strip(), v.strip()
            if v == "":
                key_for_list = k
                cfg.setdefault(k, [])
            elif v.startswith("[") and v.endswith("]"):
                inner = v[1:-1].strip()
                cfg[k] = [_scalar(t) for t in inner.split(",")] if inner else []
                key_for_list = None
            else:
                cfg[k] = _scalar(v)
                key_for_list = None
    return cfg


def _load_config(path: Path) -> dict:
    text = path.read_text()
    if yaml is not None:
        return yaml.safe_load(text) or {}
    return _mini_yaml(text)


# ---------------------------------------------------------------------------
# fittedresults.txt filtering
# ---------------------------------------------------------------------------

def _is_dataset_number(line: str) -> bool:
    p = line.split()
    return len(p) == 1 and p[0].isdigit() and len(p[0]) >= 5


def _is_data_row(line: str) -> bool:
    p = line.split()
    if len(p) < 13:
        return False
    try:
        float(p[0]); float(p[1])
        return True
    except ValueError:
        return False


def filter_fittedresults(src: Path, dst: Path, dataset: str, q2bins):
    """Copy src -> dst keeping only the matching dataset block(s), and within
    them only data rows whose Q2 (column 1) is in q2bins (all rows if q2bins
    is empty). Header lines and Plot metadata are kept verbatim."""
    lines = src.read_text().splitlines()
    blocks, i, npts = [], 1, 0          # line 0 is the original ndatasets count
    while i < len(lines):
        if not _is_dataset_number(lines[i]):
            i += 1
            continue
        head = [lines[i], lines[i + 1]]     # dataset number, label
        label = lines[i + 1].strip()
        i += 2
        meta, rows = [], []
        while i < len(lines) and not _is_dataset_number(lines[i]):
            if _is_data_row(lines[i]):
                rows.append(lines[i])
            else:
                meta.append(lines[i])
            i += 1
        if dataset and dataset not in label:
            continue
        if q2bins:
            rows = [r for r in rows
                    if any(abs(float(r.split()[0]) - q) < 1e-6 for q in q2bins)]
        if rows:
            blocks.append("\n".join(head + meta + rows))
            npts += len(rows)
    if not blocks:
        raise RuntimeError(
            f"no data selected from {src} (dataset='{dataset}', q2bins={q2bins})")
    dst.write_text(f"          {len(blocks)}\n" + "\n".join(blocks) + "\n")
    return npts


# ---------------------------------------------------------------------------
# staging + xfitter-draw invocation
# ---------------------------------------------------------------------------

_AUX_FILES = ["Results.txt", "minuit.out.txt", "parsout_0", "parsout_1"]


def _stage_fit(entry: dict, index: int, study_dir: Path, staging: Path,
               dataset: str, q2bins):
    label = entry.get("label")
    if "path" not in entry or not label:
        raise ValueError(f"fits[{index}] needs both 'label' and 'path'")
    out = (study_dir / entry["path"]).resolve()
    if (out / "output").is_dir():
        out = out / "output"
    fr = out / "fittedresults.txt"
    if not fr.is_file():
        raise FileNotFoundError(f"not found: {fr}")

    dst = staging / f"fit{index}"
    dst.mkdir(parents=True)
    n = filter_fittedresults(fr, dst / "fittedresults.txt", dataset, q2bins)
    for aux in _AUX_FILES:
        if (out / aux).is_file():
            (dst / aux).symlink_to(out / aux)
    print(f"  [{index}] {label:<24} {n:4d} points  <-  {out}")
    return dst, label


def _build_options(cfg: dict):
    # data plots only: PDF pages and shift pages have their own pipelines
    opts = ["--no-pdfs", "--no-shifts"]
    if cfg.get("therr", True):            opts.append("--therr")
    if not cfg.get("shifts", True):       opts.append("--nothshifts")
    if not cfg.get("uncorr_ticks", True): opts.append("--nouncorrerr")
    if not cfg.get("logo", True):         opts.append("--no-logo")
    if not cfg.get("upband", True):       opts.append("--noupband")
    if cfg.get("ratio_to_theory"):        opts.append("--ratio-to-theory")
    if cfg.get("filledbands"):            opts.append("--filledbands")
    if cfg.get("transparentbands"):       opts.append("--transparentbands")
    if cfg.get("ratiorange"):             opts += ["--ratiorange", str(cfg["ratiorange"])]
    if cfg.get("xrange"):                 opts += ["--xrange", str(cfg["xrange"])]
    if cfg.get("plots_per_page"):         opts += ["--plots-per-page", str(cfg["plots_per_page"])]
    opts += [str(o) for o in cfg.get("extra_options", [])]
    return opts


def _find_xfitter_draw(cfg: dict):
    """Resolve the xfitter-draw binary: config tree > env > PATH."""
    root = os.environ.get("XFITTER_ROOT", "/nfs/scratch2/ecanoner/PDF")
    tree = cfg.get("xfitter_tree",
                   os.environ.get("XFITTER_TREE", "xfitter-bartlett-fixes"))
    cand = Path(tree)
    if not cand.is_absolute():
        cand = Path(root) / tree
    exe = cand / "bin" / "xfitter-draw"
    if exe.is_file():
        return str(exe)
    found = shutil.which("xfitter-draw")
    if found:
        return found
    raise FileNotFoundError(f"xfitter-draw not found (looked in {exe} and PATH)")


def compare_xsec(study_dir: Path):
    cfg = _load_config(study_dir / "config.yaml")
    if cfg.get("type") != "xsec-comparison":
        raise ValueError(f"config type is '{cfg.get('type')}', expected 'xsec-comparison'")

    dataset = cfg.get("dataset", "")
    q2bins = [float(q) for q in (cfg.get("q2bins") or [])]
    fits = cfg.get("fits") or []
    if len(fits) < 1:
        raise ValueError("need at least one entry under 'fits'")

    staging = study_dir / ".xfdraw-staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()

    print(f"dataset: '{dataset or '(all)'}'   Q2 bins: {q2bins or '(all)'}")
    args = []
    for i, entry in enumerate(fits):
        dst, label = _stage_fit(entry, i, study_dir, staging, dataset, q2bins)
        args.append(f"{dst}:{label}")

    plots = study_dir / "plots"
    plots.mkdir(exist_ok=True)
    outdir = staging / "out"
    outdir.mkdir()

    exe = _find_xfitter_draw(cfg)
    cmd = [exe] + _build_options(cfg) + ["--outdir", str(outdir)] + args
    print("running:", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    tail = "\n".join((res.stdout + res.stderr).splitlines()[-6:])
    if res.returncode != 0 or not (outdir / "plots.pdf").is_file():
        print(tail)
        raise RuntimeError(f"xfitter-draw failed (exit {res.returncode})")

    shutil.copy2(outdir / "plots.pdf", plots / "xsec_comparison.pdf")
    for tex in ("chi2.tex", "par.tex"):
        if (outdir / tex).is_file():
            shutil.copy2(outdir / tex, plots / tex)
    shutil.rmtree(staging)

    # therr sanity note: warn when bands were requested but a fit has none
    if cfg.get("therr", True):
        for i, entry in enumerate(fits):
            out = (study_dir / entry["path"]).resolve()
            fr = (out / "output" / "fittedresults.txt")
            if not fr.is_file():
                fr = out / "fittedresults.txt"
            nz = sum(1 for l in fr.read_text().splitlines()
                     if _is_data_row(l) and (float(l.split()[8]) != 0.0
                                             or float(l.split()[9]) != 0.0))
            if nz == 0:
                print(f"  WARNING: '{entry['label']}' has all-zero therr "
                      f"(output predates the band fix?) -> no band drawn")

    print(f"\nWrote {plots / 'xsec_comparison.pdf'}")
