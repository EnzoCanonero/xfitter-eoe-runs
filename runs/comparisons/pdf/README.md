# PDF comparisons

This tool overlays parton distributions from any configured set of fits,
including their Hessian uncertainty bands and ratios to a chosen reference.
The scale, x range, observables, fit labels and reference are configurable.
It reads existing outputs without running a fit.

See [installation](../../../docs/installation.md) for the environment.
[HERA study definitions](../../../docs/hera-study.md),
[HERA comparison examples](../../../docs/hera-comparisons.md) and
[paper reproduction](../../../docs/reproducing-paper.md) describe the supplied
scientific application separately from this general interface.

## Workspace and configuration

Create a workspace under `runs/comparisons/pdf/<setup>/<comparison>/` containing
`config.yaml`. Run commands from the repository root. The paths and names below
are placeholders for your own fits:

```yaml
type: pdf-comparison
Q2: 25.0
x_min: 0.001
x_max: 0.7
n_points: 150
observables: [uv, dv, gluon]
error_type: symmetric
ratio_reference: Reference
ratio_ylim: [0.8, 1.2]
fits:
  - label: Reference
    path: ../../../../fits/my-setup/reference
    source: xfitter-grid
  - label: Alternative
    path: ../../../../fits/my-setup/alternative
    source: xfitter-grid
```

One or more fit entries are accepted. Their labels are arbitrary; no particular
physical setup or uncertainty treatment is required. Relative fit paths are
resolved from the workspace directory. Absolute paths also work.

| Setting | Meaning and default |
| --- | --- |
| `Q2` | Positive evaluation scale in GeV²; default `10.0` |
| `x_min`, `x_max` | Positive x limits within each input's coverage; defaults `0.0001`, `0.9` |
| `n_points` | Number of logarithmically spaced x samples; default `100` |
| `observables` | Ordered subset of `uv`, `dv`, `gluon`, `sea`; default all four |
| `error_type` | `symmetric` or `asymmetric` Hessian prescription; default `asymmetric` |
| `ratio_reference` | Zero-based fit index or an exact fit label; default `0` |
| `ratio_ylim` | Ratio-axis limits; default `[0.6, 1.4]`; `null` enables automatic limits |

The supported observables are x-weighted distributions: `uv` = xuᵥ, `dv` = xdᵥ,
`gluon` = xg and `sea` = 2x(ū + d̄ + s̄). Other flavour combinations are not
selectable through configuration.

## Input formats and dependencies

Each fit can use either input format, and a comparison may mix them:

| Source | Required input |
| --- | --- |
| `source: xfitter-grid` | `path` names a fit root containing `output/pdfs_q2val_NN.txt` and its Pumplin member grids |
| `source: lhapdf` with `path` | `<fit>/output/<set>/<set>.info` and `<set>_*.dat`; `set` defaults to `proton` |
| `source: lhapdf` with `lhapdf_set` | An installed set available on LHAPDF's search path; no local fit path is needed |

`lhapdf` is the default source when `source` is omitted. For example:

```yaml
fits:
  - label: Local fit
    source: lhapdf
    path: ../../../../fits/my-setup/reference
    set: proton
  - label: Installed reference
    source: lhapdf
    lhapdf_set: YOUR_INSTALLED_SET
```

Native grids must have the standard two-line xFitter header and flavour-column
layout. The reader finds exactly one central grid whose header matches `Q2`;
it does not interpolate between scales. The two-digit suffix `NN` identifies
that scale's files. Error members are named
`pdfs_q2val_s<direction>p_NN.txt` and `pdfs_q2val_s<direction>m_NN.txt`.
Each discovered direction must have both signs, with the same table shape and
x grid as the central file. Interpolation in log(x) stays inside the input
range; extrapolation is rejected. Keep the full member set to reproduce bands.

Uncertainties use Hessian member formulas, including LHAPDF `symmhessian`
sets. There is no Monte Carlo replica uncertainty prescription or automatic
confidence-level rescaling. A central-only input produces no uncertainty band.
Each ratio divides a curve and its band by the reference central distribution;
it does not propagate an additional denominator uncertainty. Zero reference
values are omitted from the ratio.

The plotting environment needs Python, NumPy, Matplotlib, PyYAML and LHAPDF
Python bindings, including for native-grid input. The wrapper uses the current
Python if these imports work, otherwise it sources the view selected by
`LCG_SETUP`. No xFitter executable is invoked. Local fit outputs and externally
installed LHAPDF sets must be supplied separately from the checkout.

## Generate and check outputs

After creating the example workspace and supplying its inputs:

```bash
workspace=runs/comparisons/pdf/my-setup/my-comparison
scripts/plot-pdf-comparison "$workspace"
```

The command replaces these files under the chosen workspace:

| File | Content | Page size |
| --- | --- | --- |
| `plots/pdf_comparison.pdf` | Absolute and ratio panels side by side | 864 × 432 pt |
| `plots/pdf_comparison_absolute.pdf` | Absolute panels only | 504 × 432 pt |
| `plots/pdf_comparison_ratio.pdf` | Ratio panels only | 504 × 432 pt |

Every file has one page per configured observable, in the configured order.
No CSV is emitted. With Poppler installed, inspect metadata with
`pdfinfo "$workspace/plots/pdf_comparison.pdf"`; confirm that the page count
matches `observables`. Inspect the curves, bands, scale and ratio denominator.
The console lists resolved inputs and native-grid uncertainty directions.

## Labels and presentation options

Each fit accepts `label`, `color` and `linestyle`. Optional `setup` and
`treatment` strings distinguish shared information from curve labels. When all
fits provide both fields, the renderer derives a common heading and legends;
otherwise it retains the explicit fit labels. Fits with the same setup and
treatment retain distinct method labels when supplied.

The optional `presentation` mapping changes display settings:

| Key | Effect |
| --- | --- |
| `title` | Override the heading; `null` hides it while retaining an existing reserved heading margin |
| `use_fit_labels` | Use explicit fit labels instead of metadata-derived legend text |
| `ratio_reference_label` | Override the displayed denominator name; does not change the numerical `ratio_reference` |
| `legend_fontsize` | Override the legend size in all three output variants |

The [HERA presentation conventions](../../../docs/hera-comparisons.md#typography-and-presentation)
record the supplied study's labels and typography. Related tools:
[cross-section comparisons](../xsec/README.md) and
[regional χ² tables](../regions/README.md).
