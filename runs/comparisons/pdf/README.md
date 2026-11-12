# PDF comparisons

[Workflows](../../README.md) · [Installation](../../../docs/installation.md) ·
[HERA figures](../../../docs/hera-study.md)

Overlay completed fits' PDFs, Hessian uncertainty bands and ratios to a chosen
reference. The command does not run fits and needs LHAPDF Python bindings.

## Configuration

Create `runs/comparisons/pdf/my-setup/my-comparison/config.yaml`:

```yaml
type: pdf-comparison
Q2: 25.0
x_min: 0.001
x_max: 0.7
observables: [uv, dv, gluon]
error_type: symmetric
ratio_reference: Reference
fits:
  - {label: Reference, path: ../../../../fits/my-setup/reference, source: xfitter-grid}
  - {label: Alternative, path: ../../../../fits/my-setup/alternative, source: xfitter-grid}
```

Replace the fit paths with your outputs. Paths are relative to this workspace,
or absolute. [Complete HERA example](herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected/config.yaml).

- **Native grids:** `source: xfitter-grid` reads the fit's `output/` grids.
  Keep the central and uncertainty members at the requested `Q2` (GeV²);
  there is no interpolation between scales.
- **LHAPDF:** use `source: lhapdf` with `path` and `set` (default `proton`),
  or `lhapdf_set: SET_NAME` for an installed set.
- **Quantities:** `uv`, `dv`, `gluon`, `sea` mean xuᵥ, xdᵥ, xg, 2x(ū + d̄ + s̄).
- **Bands and ratios:** `error_type` is `symmetric` or `asymmetric` (Hessian,
  not replica uncertainties). Ratios divide by the reference central PDF.
- **Display:** `ratio_ylim` sets ratio limits; each fit accepts `color` and
  `linestyle`. Choose an x range covered by all inputs.

## Run

From the repository root:

```bash
workspace=runs/comparisons/pdf/my-setup/my-comparison
scripts/plot-pdf-comparison "$workspace"
```

## Outputs

Each file has one page per observable, in the configured order:

- `plots/pdf_comparison.pdf`: absolute and ratio panels together.
- `plots/pdf_comparison_absolute.pdf`: absolute panels.
- `plots/pdf_comparison_ratio.pdf`: ratio panels.
