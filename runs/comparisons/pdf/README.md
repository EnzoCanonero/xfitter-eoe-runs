# PDF comparisons

[Workflows](../../README.md) · [Installation](../../../docs/installation.md) ·
[HERA figures](../../../docs/hera-study.md)

Overlay completed fits' PDFs, Hessian uncertainty bands and ratios to a chosen
reference. The command does not run fits and needs LHAPDF Python bindings.

## Configuration

Create `runs/comparisons/pdf/my-setup/my-comparison/config.yaml`. All options:

```yaml
type: pdf-comparison
Q2: 4.0
x_min: 1.0e-4
x_max: 0.9
n_points: 100
observables: [uv, dv, gluon, sea]
error_type: asymmetric
ratio_reference: 0
ratio_ylim: [0.6, 1.4]
fits:
  - label: Gaussian
    path: ../../../../fits/my-setup/gaussian
    source: xfitter-grid
    setup: "HERAPDF2.0, NNLO, RTOPT"
    treatment: Gaussian
    color: "#1f77b4"
    linestyle: "-"
  - label: EoE
    path: ../../../../fits/my-setup/eoe
    source: lhapdf
    set: proton
    setup: "HERAPDF2.0, NNLO, RTOPT"
    treatment: EoE
  # - {label: External, source: lhapdf, lhapdf_set: SET_NAME}
presentation:
  title: "HERAPDF2.0, NNLO, RTOPT"
  use_fit_labels: false
  ratio_reference_label: Gaussian
  legend_fontsize: 15
```

- `type` (required): `pdf-comparison`.
- `Q2` (default `10`): scale in GeV². With `xfitter-grid` it must be one of the
  fit's output scales (`Q2VAL` in the steering); there is no interpolation.
- `x_min`, `x_max` (default `1e-4`, `0.9`): x range, covered by all inputs.
- `n_points` (default `100`): number of log-spaced x points.
- `observables` (default all): pages to draw, in order: `uv` (xuᵥ), `dv`
  (xdᵥ), `gluon` (xg), `sea` (2x(ū + d̄ + s̄)).
- `error_type` (default `asymmetric`): Hessian bands, `symmetric` or
  `asymmetric`.
- `ratio_reference` (default `0`): fit used as ratio denominator, by index
  (from 0) or `label`.
- `ratio_ylim` (default `[0.6, 1.4]`): ratio-panel limits; `null` for automatic.
- `fits` (required): curves to draw.
  - `label`: legend label (default: the fit directory or set name).
  - `source` (default `lhapdf`): `xfitter-grid` reads the fit's
    `output/pdfs_q2val_*` grids; `lhapdf` reads an LHAPDF set.
  - `path`: fit directory, relative to this workspace or absolute.
  - `set` (default `proton`, `lhapdf` only): set directory in the fit's `output/`.
  - `lhapdf_set` (`lhapdf` only): installed LHAPDF set, instead of `path`.
  - `setup`, `treatment`: optional; when every fit has both, the shared part
    becomes the heading and the legend shows what differs.
  - `color`, `linestyle`: matplotlib styles (default: a colour cycle and `-`).
- `presentation`: optional overrides of the automatic labels.
  - `title`: heading; `null` hides it.
  - `use_fit_labels` (default `false`): legends use `label` instead of
    `setup`/`treatment`.
  - `ratio_reference_label`: name of the ratio denominator in the axis label.
  - `legend_fontsize` (default `15`).

Ratios divide by the reference central PDF.
[HERA configuration](herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected/config.yaml).

## Run

```bash
workspace=runs/comparisons/pdf/my-setup/my-comparison
scripts/plot-pdf-comparison "$workspace"
```

## Outputs

Each file has one page per observable, in the configured order:

- `plots/pdf_comparison.pdf`: absolute and ratio panels together.
- `plots/pdf_comparison_absolute.pdf`: absolute panels.
- `plots/pdf_comparison_ratio.pdf`: ratio panels.
