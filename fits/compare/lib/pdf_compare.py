"""
PDF comparison for individual fits.

Overlays the parton distributions from an arbitrary number of single fits (each of
which writes its own LHAPDF set under ``<fit>/output/<set>``) into a single multi-page
PDF, one page per observable, with a 2-panel layout (central + uncertainty band on the
left, ratio-to-reference on the right).

Driven by a study ``config.yaml`` (see ``compare_pdfs``); mirrors the UX of the scans
framework but is self-contained.
"""

from pathlib import Path
import math
import re
import shutil
import tempfile

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import yaml

import lhapdf

# -------------------------------------------------------------------------
# Observable definitions (styling basis: the shared comparison template)
#   u_v(x)  = xf(2)  - xf(-2)
#   d_v(x)  = xf(1)  - xf(-1)
#   gluon   = xf(21)
#   sea     = 2*( xf(-2) + xf(-1) + xf(-3) )
# LHAPDF's xfxQ already returns x*f(x), so these are the x-weighted quantities.
# -------------------------------------------------------------------------
OBSERVABLE_FUNCS = {
    "uv":    lambda pdf, x, Q: pdf.xfxQ(2, x, Q) - pdf.xfxQ(-2, x, Q),
    "dv":    lambda pdf, x, Q: pdf.xfxQ(1, x, Q) - pdf.xfxQ(-1, x, Q),
    "gluon": lambda pdf, x, Q: pdf.xfxQ(21, x, Q),
    "sea":   lambda pdf, x, Q: 2 * (pdf.xfxQ(-2, x, Q) + pdf.xfxQ(-1, x, Q)
                                    + pdf.xfxQ(-3, x, Q)),
}

YLABELS = {
    "uv":    r'$x\,u_v(x)$',
    "dv":    r'$x\,d_v(x)$',
    "gluon": r'$x\,g(x)$',
    "sea":   r'$2x\,[\bar{u}(x)+\bar{d}(x)+\bar{s}(x)]$',
}

TITLES = {
    "uv":    r'$u_v$',
    "dv":    r'$d_v$',
    "gluon": r'gluon',
    "sea":   r'sea',
}

DEFAULT_OBSERVABLES = ["uv", "dv", "gluon", "sea"]

# Default colour cycle used when a fit does not specify its own colour.
_DEFAULT_COLORS = [
    "#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e",
    "#8c564b", "#e377c2", "#17becf", "#bcbd22", "#7f7f7f",
]


# =========================================================================
# Configuration
# =========================================================================
class CompareConfig:
    """Parsed config.yaml for a PDF-comparison study.

    Follows the StudyConfig loader style used in scans/lib/config.py: yaml.safe_load
    with property accessors and clear errors on missing required fields.
    """

    def __init__(self, config_file: Path):
        self.config_file = Path(config_file)
        self.study_dir = self.config_file.parent
        with open(self.config_file) as f:
            self.data = yaml.safe_load(f) or {}

        if "fits" not in self.data or not self.data["fits"]:
            raise ValueError("config.yaml must specify a non-empty 'fits' list")

    @property
    def Q2(self) -> float:
        return float(self.data.get("Q2", 10.0))

    @property
    def Q(self) -> float:
        return math.sqrt(self.Q2)

    @property
    def x_min(self) -> float:
        return float(self.data.get("x_min", 1.0e-4))

    @property
    def x_max(self) -> float:
        return float(self.data.get("x_max", 0.9))

    @property
    def n_points(self) -> int:
        return int(self.data.get("n_points", 100))

    @property
    def observables(self) -> list:
        obs = self.data.get("observables", DEFAULT_OBSERVABLES)
        for o in obs:
            if o not in OBSERVABLE_FUNCS:
                raise ValueError(f"unknown observable '{o}' "
                                 f"(choose from {list(OBSERVABLE_FUNCS)})")
        return list(obs)

    @property
    def error_type(self) -> str:
        et = self.data.get("error_type", "asymmetric")
        if et not in ("symmetric", "asymmetric"):
            raise ValueError("error_type must be 'symmetric' or 'asymmetric'")
        return et

    @property
    def ratio_ylim(self):
        yl = self.data.get("ratio_ylim", [0.6, 1.4])
        return None if yl is None else tuple(yl)

    @property
    def fits(self) -> list:
        return self.data["fits"]

    def x_grid(self) -> np.ndarray:
        return np.logspace(math.log10(self.x_min), math.log10(self.x_max), self.n_points)

    def reference_index(self, labels) -> int:
        """Resolve ratio_reference (0-based index or a label string) to an index."""
        ref = self.data.get("ratio_reference", 0)
        if isinstance(ref, int):
            if not 0 <= ref < len(labels):
                raise ValueError(f"ratio_reference index {ref} out of range "
                                 f"(0..{len(labels) - 1})")
            return ref
        # string: match against labels
        if ref in labels:
            return labels.index(ref)
        raise ValueError(f"ratio_reference '{ref}' does not match any fit label "
                         f"({labels})")


# =========================================================================
# LHAPDF set loading (with unique-name staging to avoid 'proton' collisions)
# =========================================================================
def _sanitize(name: str) -> str:
    """Make a string safe to use as an LHAPDF set name."""
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") or "set"


def _stage_local_set(set_dir: Path, set_name: str, uniq: str, staging_root: Path):
    """Symlink a fit's LHAPDF set under a unique name so multiple 'proton' sets can
    coexist. LHAPDF requires dir name == set name == member/info file prefix.

    Returns the unique set name to load.
    """
    info_src = set_dir / f"{set_name}.info"
    if not info_src.exists():
        raise FileNotFoundError(f"LHAPDF info file not found: {info_src}")

    dest_dir = staging_root / uniq
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / f"{uniq}.info").symlink_to(info_src.resolve())

    members = sorted(set_dir.glob(f"{set_name}_*.dat"))
    if not members:
        raise FileNotFoundError(f"no member files {set_name}_*.dat in {set_dir}")
    for member in members:
        suffix = member.name[len(set_name):]        # e.g. '_0000.dat'
        (dest_dir / f"{uniq}{suffix}").symlink_to(member.resolve())
    return uniq


def _resolve_fit(entry: dict, index: int, study_dir: Path, staging_root: Path):
    """Turn a config 'fits' entry into (label, lhapdf_name, color, linestyle)."""
    color = entry.get("color", _DEFAULT_COLORS[index % len(_DEFAULT_COLORS)])
    linestyle = entry.get("linestyle", "-")

    if "lhapdf_set" in entry:
        name = entry["lhapdf_set"]
        label = entry.get("label", name)
        return label, name, color, linestyle

    if "path" not in entry:
        raise ValueError(f"fit entry #{index} must have 'path' or 'lhapdf_set'")

    fit_dir = (study_dir / entry["path"]).resolve()
    set_name = entry.get("set", "proton")
    set_dir = fit_dir / "output" / set_name
    if not set_dir.is_dir():
        raise FileNotFoundError(f"set directory not found: {set_dir}")

    label = entry.get("label", fit_dir.name)
    uniq = f"cmp{index}_{_sanitize(label)}"
    name = _stage_local_set(set_dir, set_name, uniq, staging_root)
    return label, name, color, linestyle


def _hessian_band(f0, members, is_symmhessian, symmetric):
    """Hessian uncertainty at one point from the error-member values.

    Computed directly from the members (not via PDFSet.uncertainty, whose CL
    rescaling misbehaves on xFitter-written sets: it can return scale=0). This is
    the standard 1-sigma Hessian formula.
      - symmhessian: N directions,  err = sqrt(sum_k (f_k - f0)^2)
      - hessian:     N +/- pairs,   err+ = sqrt(sum_i max(f_i+ - f0, f_i- - f0, 0)^2)
                                     err- = sqrt(sum_i max(f0 - f_i+, f0 - f_i-, 0)^2)
                                     symm = 0.5*sqrt(sum_i (f_i+ - f_i-)^2)
    """
    if is_symmhessian or len(members) % 2 == 1:
        s = math.sqrt(sum((v - f0) ** 2 for v in members))
        return s, s
    ep2 = em2 = sym2 = 0.0
    for k in range(0, len(members) - 1, 2):
        a, b = members[k], members[k + 1]
        ep2 += max(a - f0, b - f0, 0.0) ** 2
        em2 += max(f0 - a, f0 - b, 0.0) ** 2
        sym2 += (a - b) ** 2
    if symmetric:
        s = 0.5 * math.sqrt(sym2)
        return s, s
    return math.sqrt(ep2), math.sqrt(em2)


def _evaluate_set(pset, pdfs, obs_func, x_vals, Q, error_type):
    """Return (central, err_plus, err_minus) arrays for one set/observable.

    Auto-detects uncertainties: a set with >1 member gets a Hessian band computed
    directly from the members (honouring the set's ErrorType: symmhessian vs the
    default hessian +/- pairs); a single-member set gets zero-width errors.
    """
    central = np.array([obs_func(pdfs[0], x, Q) for x in x_vals])

    if len(pdfs) <= 1:
        zeros = np.zeros_like(central)
        return central, zeros, zeros

    is_symmhessian = "symmhessian" in (pset.errorType or "").lower()
    symmetric = (error_type == "symmetric")
    err_plus = np.empty_like(central)
    err_minus = np.empty_like(central)
    for i, x in enumerate(x_vals):
        members = [obs_func(p, x, Q) for p in pdfs[1:]]
        err_plus[i], err_minus[i] = _hessian_band(central[i], members,
                                                   is_symmhessian, symmetric)
    return central, err_plus, err_minus


# =========================================================================
# Plotting
# =========================================================================
def _plot_observable(pdf_pages, obs, curves, ref_idx, Q2, ratio_ylim, x_min, x_max):
    """Render one observable page (central + ratio panels) into the open PdfPages."""
    fig, (ax_main, ax_ratio) = plt.subplots(1, 2, figsize=(12, 6))
    x_vals = curves[0]["x"]
    ref = curves[ref_idx]["obs"][obs]
    ref_central = ref["central"]

    with np.errstate(divide="ignore", invalid="ignore"):
        for c in curves:
            data = c["obs"][obs]
            central = data["central"]
            has_band = np.any(data["err_plus"] != 0) or np.any(data["err_minus"] != 0)

            # --- central panel ---
            ax_main.semilogx(x_vals, central, label=c["label"],
                             color=c["color"], linestyle=c["linestyle"])
            if has_band:
                ax_main.fill_between(x_vals,
                                     central - data["err_minus"],
                                     central + data["err_plus"],
                                     color=c["color"], alpha=0.25, linewidth=0)

            # --- ratio panel (to reference central) ---
            ratio = np.where(ref_central != 0, central / ref_central, np.nan)
            ax_ratio.semilogx(x_vals, ratio, color=c["color"], linestyle=c["linestyle"])
            if has_band:
                lo = np.where(ref_central != 0,
                              (central - data["err_minus"]) / ref_central, np.nan)
                hi = np.where(ref_central != 0,
                              (central + data["err_plus"]) / ref_central, np.nan)
                ax_ratio.fill_between(x_vals, lo, hi, color=c["color"],
                                      alpha=0.25, linewidth=0)

    ax_main.set_ylabel(YLABELS[obs], fontsize=14)
    ax_main.set_xlabel("x", fontsize=13)
    ax_main.set_xlim(x_min, x_max)
    ax_main.grid(True, which="both", ls="--", lw=0.5)
    ax_main.plot([], [], ' ', label=rf'$Q^2 = {Q2:g}\ \mathrm{{GeV}}^2$')
    ax_main.legend(fontsize=11)
    ax_main.set_title(f"{TITLES[obs]}", fontsize=14)

    ax_ratio.axhline(1, color="black", linestyle=":", lw=1)
    ax_ratio.set_xlabel("x", fontsize=13)
    ax_ratio.set_ylabel(f"Ratio to {curves[ref_idx]['label']}", fontsize=13)
    ax_ratio.set_xlim(x_min, x_max)
    if ratio_ylim is not None:
        ax_ratio.set_ylim(*ratio_ylim)
    ax_ratio.grid(True, which="both", ls="--", lw=0.5)

    fig.tight_layout()
    pdf_pages.savefig(fig)
    plt.close(fig)


# =========================================================================
# Entry point
# =========================================================================
def compare_pdfs(study_dir: Path):
    """Load every fit in the study's config.yaml and write plots/pdf_comparison.pdf."""
    study_dir = Path(study_dir)
    config = CompareConfig(study_dir / "config.yaml")

    x_vals = config.x_grid()
    Q = config.Q
    error_type = config.error_type

    staging_root = Path(tempfile.mkdtemp(prefix="pdfcompare_"))
    try:
        lhapdf.pathsPrepend(str(staging_root))

        # Resolve + load every fit up front.
        curves = []
        for i, entry in enumerate(config.fits):
            label, name, color, linestyle = _resolve_fit(entry, i, study_dir, staging_root)
            print(f"  [{i}] {label}  <-  {name}")
            pset = lhapdf.getPDFSet(name)      # load members once, reuse across observables
            pdfs = pset.mkPDFs()
            obs_data = {}
            for obs in config.observables:
                central, ep, em = _evaluate_set(pset, pdfs, OBSERVABLE_FUNCS[obs],
                                                x_vals, Q, error_type)
                obs_data[obs] = {"central": central, "err_plus": ep, "err_minus": em}
            curves.append({"label": label, "color": color, "linestyle": linestyle,
                           "x": x_vals, "obs": obs_data})

        labels = [c["label"] for c in curves]
        ref_idx = config.reference_index(labels)

        plots_dir = study_dir / "plots"
        plots_dir.mkdir(exist_ok=True)
        out_pdf = plots_dir / "pdf_comparison.pdf"
        with PdfPages(out_pdf) as pdf_pages:
            for obs in config.observables:
                _plot_observable(pdf_pages, obs, curves, ref_idx, config.Q2,
                                 config.ratio_ylim, config.x_min, config.x_max)

        print(f"\nWrote {out_pdf}  ({len(config.observables)} pages, "
              f"reference = '{labels[ref_idx]}')")
        return out_pdf
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)
