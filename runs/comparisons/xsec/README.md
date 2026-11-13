# Cross-section comparisons

[Workflows](../../README.md) · [Installation](../../../docs/installation.md) ·
[HERA Figure 3](../../../docs/hera-study.md#figure-3-low-q2-cross-sections)

Compare existing DIS predictions with data using `xfitter-draw`. Each fit needs
`fittedresults.txt` in its directory or `output/`; no fits are rerun.

## Configuration

Create `runs/comparisons/xsec/my-setup/my-comparison/config.yaml`. All options:

```yaml
type: xsec-comparison
panels:
  - {dataset: "Sample A", q2: 25.0}
  - {dataset: "Sample B", q2: 100.0}
# dataset: "Sample A"
# q2bins: [25.0, 35.0]
fits:
  - {label: Gaussian, path: ../../../../fits/my-setup/gaussian, setup: "HERAPDF2.0, NNLO, RTOPT", treatment: Gaussian}
  - {label: EoE, path: ../../../../fits/my-setup/eoe, setup: "HERAPDF2.0, NNLO, RTOPT", treatment: EoE}
therr: true
shifts: true
uncorr_ticks: true
logo: true
upband: true
show_setup_annotation: true
ratio_to_theory: false
# ratiorange: "0.9:1.1"
# xrange: "1e-5:0.02"
plots_per_page: 4
filledbands: false
transparentbands: false
extra_options: []
xfitter_tree: xfitter-master
```

- `type` (required): `xsec-comparison`.
- `panels`: Q² slices to draw; takes precedence over `dataset` and `q2bins`.
  - `dataset`: substring of the dataset name in `fittedresults.txt`.
  - `q2`: Q² of the slice, in GeV².
- `dataset`: without `panels`, substring selecting datasets (default all).
- `q2bins`: without `panels`, Q² values to draw (default all).
- `fits` (required): fits to overlay; the first provides the data points.
  - `label`: legend label.
  - `path`: fit directory with `fittedresults.txt` in it or in `output/`,
    relative to this workspace or absolute.
  - `setup`, `treatment`: optional; when every fit has both, the shared part
    becomes the heading and the legend shows what differs.
- `therr` (default `true`): theory-uncertainty bands, when the fits have them.
- `shifts` (default `true`): dashed theory-plus-shifts curves.
- `uncorr_ticks` (default `true`): uncorrelated-uncertainty ticks on the data.
- `logo` (default `true`): xFitter logo.
- `upband` (default `true`): bands in the upper panel.
- `show_setup_annotation` (default `true`): shared setup heading.
- `ratio_to_theory` (default `false`): ratios to theory instead of data.
- `ratiorange`, `xrange`: optional display limits, as `"min:max"`.
- `plots_per_page` (default `4`): panels per page.
- `filledbands`, `transparentbands` (default `false`): band style.
- `extra_options` (default empty): extra `xfitter-draw` options, e.g.
  `["--no-tables"]`.
- `xfitter_tree` (default from `.env`): xFitter build providing `xfitter-draw`.

[HERA configuration](herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected-low-q2/config.yaml).

## Run

```bash
workspace=runs/comparisons/xsec/my-setup/my-comparison
scripts/plot-xsec "$workspace"
```

The command loads the xFitter environment from `.env`; `xfitter-draw` needs
ROOT, Ghostscript and, for summary tables, `pdflatex`.

## Outputs

`plots/xsec_comparison.pdf` contains the selected panels, followed by any
fit-summary pages. The renderer's `chi2.tex` and `par.tex` are also copied to
`plots/` when produced. Summary tables describe the full fits.
