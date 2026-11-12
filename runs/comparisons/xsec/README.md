# Cross-section comparisons

[Workflows](../../README.md) · [Installation](../../../docs/installation.md) ·
[HERA Figure 3](../../../docs/hera-study.md#figure-3-low-q2-cross-sections)

Compare existing DIS predictions with data using `xfitter-draw`. Each fit needs
`fittedresults.txt` in its directory or `output/`; no fits are rerun.

## Configuration

Create `runs/comparisons/xsec/my-setup/my-comparison/config.yaml`:

```yaml
type: xsec-comparison
panels:
  - {dataset: "Sample A", q2: 25.0}
  - {dataset: "Sample B", q2: 100.0}
fits:
  - {label: Reference, path: ../../../../fits/my-setup/reference}
  - {label: Alternative, path: ../../../../fits/my-setup/alternative}
therr: true
plots_per_page: 1
```

Replace dataset names, Q² values and paths with your inputs. Fit paths are
relative to this workspace, or absolute.
[Complete HERA example](herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected-low-q2/config.yaml).

- `panels` selects dataset-substring/Q² pairs. Alternatively, use `dataset`
  and `q2bins` to select several slices of the same dataset.
- `therr` shows theory bands when the input has nonzero theory uncertainties.
- `xrange` and `ratiorange` set display limits, e.g. `"0.001:0.5"`.
- `ratio_to_theory: true` changes ratios from data to theory denominators.
- `extra_options: ["--no-tables"]` omits xFitter's fit-summary tables.

## Run

Configure `.env` as in the installation guide, then run from the repository root:

```bash
workspace=runs/comparisons/xsec/my-setup/my-comparison
scripts/plot-xsec "$workspace"
```

The command initializes the xFitter environment. Its `xfitter-draw` executable
uses ROOT and Ghostscript; `pdflatex` is needed when summary tables are enabled.

## Outputs

`plots/xsec_comparison.pdf` contains the selected panels, followed by any
fit-summary pages. The renderer's `chi2.tex` and `par.tex` are also copied to
`plots/` when produced. Summary tables describe the full fits.
