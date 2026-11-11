# HERA comparison examples and presentation

This document records the supplied HERA comparison configurations, their paper
roles and their presentation conventions. The general interfaces are described
in the [PDF](../runs/comparisons/pdf/README.md) and
[cross-section](../runs/comparisons/xsec/README.md) guides. See the
[HERA study definitions](hera-study.md) for setup and treatment terminology,
and [paper reproduction](reproducing-paper.md) for the full execution order.

The commands below run from the repository root, use completed fit outputs and
replace derived plots. They do not submit jobs. The configurations
select particular HERA examples; the comparison tools also accept other
compatible inputs and kinematic ranges.

## PDF workspaces

Fit paths in this table are relative to `runs/fits/`. Each requires its
populated `output/` directory.

| Comparison configuration | Input fits | Paper use |
| --- | --- | --- |
| [HERAPDF2.0: Gaussian versus selected EoE](../runs/comparisons/pdf/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected/config.yaml) | `herapdf20-nnlo-rtopt/{gaussian,eoe-selected}` | Figure 2 |
| [HERAPDF-BG: Gaussian versus selected EoE](../runs/comparisons/pdf/herapdf-bg-nnlo-rtopt/gaussian-vs-eoe-selected/config.yaml) | `herapdf-bg-nnlo-rtopt/{gaussian,eoe-selected}` | Figure 4 |
| [Resummed HERAPDF-BG: Gaussian versus selected EoE](../runs/comparisons/pdf/herapdf-bg-nnlo-nllx-fonll-c/gaussian-vs-eoe-selected/config.yaml) | `herapdf-bg-nnlo-nllx-fonll-c/{gaussian,eoe-selected}` | Figure 5 |
| [Informed EoE across three setups](../runs/comparisons/pdf/cross-setups/eoe-informed/config.yaml) | `eoe-informed` in each of the three setup directories above | Figure 6 |
| [Numerical versus 2 iterations](../runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter02/config.yaml) | `herapdf20-nnlo-rtopt/{eoe-selected,eoe-selected-iter02}` | Figure 7, Appendix A |
| [Numerical versus 4 iterations](../runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter04/config.yaml) | `herapdf20-nnlo-rtopt/{eoe-selected,eoe-selected-iter04}` | Figure 7, Appendix A |
| [Numerical versus 8 iterations](../runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter08/config.yaml) | `herapdf20-nnlo-rtopt/{eoe-selected,eoe-selected-iter08}` | Figure 7, Appendix A |

The two RTOPT setups use NNLO evolution with HERAPDF2.0 or HERAPDF-BG
parametrisations. The resummed setup uses HERAPDF-BG, NNLO+NLLₓ and FONLL-C.
Selected EoE uses the corresponding forward-selection endpoint; informed EoE
uses the physically motivated source assignment. The iteration comparisons
hold the HERAPDF2.0 setup and selected EoE treatment fixed while comparing
numerical fitting with iterative nuisance profiling.

All seven configurations use `source: xfitter-grid`, Q² = 4 GeV², symmetric
Hessian bands and 100 logarithmically spaced x samples from 10⁻⁴ to 0.9.
The reader selects the central grid by its header scale:

| Setup | Central grid at Q² = 4 GeV² | Error-member suffix |
| --- | --- | --- |
| HERAPDF2.0, NNLO, RTOPT | `output/pdfs_q2val_03.txt` | `_03.txt` |
| HERAPDF-BG, NNLO, RTOPT | `output/pdfs_q2val_03.txt` | `_03.txt` |
| HERAPDF-BG, NNLO+NLLₓ, FONLL-C | `output/pdfs_q2val_04.txt` | `_04.txt` |

Each fit also needs its complete matching `pdfs_q2val_s<direction>p_NN.txt`
and `pdfs_q2val_s<direction>m_NN.txt` files. No external LHAPDF set supplies
these curves, although the plotting runtime still imports the LHAPDF bindings.

For example:

```bash
workspace=runs/comparisons/pdf/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected
scripts/plot-pdf-comparison "$workspace"
```

The [reproduction guide](reproducing-paper.md#regenerate-the-native-figure-files)
lists all seven commands. Each workspace produces
`plots/pdf_comparison.pdf`, `plots/pdf_comparison_absolute.pdf` and
`plots/pdf_comparison_ratio.pdf`. The combined pages are 864 × 432 pt;
individual panels are 504 × 432 pt. HERAPDF2.0 Gaussian/EoE and the three
iteration workspaces have four pages in `uv`, `dv`, `gluon`, `sea` order.
The BG, resummed and informed comparisons have three: `uv`, `dv`, `gluon`.
The manuscript uses the first three observables.

All ratios use the first fit's central distribution: Gaussian for Figures 2,
4 and 5; informed HERAPDF2.0 for Figure 6; Numerical for Figure 7. Inspect the
page count, labels, bands and denominator in each output. Final manuscript
assembly is separate from these native files.

## Typography and presentation

The PDF renderer uses 22 pt panel titles and axis labels, 18 pt ticks, 15 pt
legends and 16 pt setup headings in all three output variants. Figure 6's
configuration overrides the legend to 13 pt, including its Q² entry.

| Comparison | Heading | Curve labels | Ratio label |
| --- | --- | --- | --- |
| Figure 2 | HERAPDF2.0, NNLO, RTOPT | Gaussian / EoE | Ratio to Gaussian |
| Figure 4 | HERAPDF-BG, NNLO, RTOPT | Gaussian / EoE | Ratio to Gaussian |
| Figure 5 | HERAPDF-BG, NNLO+NLLₓ, FONLL-C | Gaussian / EoE | Ratio to Gaussian |
| Figure 6 | Hidden | HERAPDF2.0 / HERAPDF-BG / HERAPDF-BG NNLO+NLL | Ratio to HERAPDF2.0 |
| Figure 7 | HERAPDF2.0, NNLO, RTOPT | Numerical / Iterative | Ratio to Numerical |

Fit entries separate full `setup` metadata from the displayed `treatment` and
`label`. The spelling `NLL_x` in setup metadata renders the subscript. Figure 6
uses these overrides:

```yaml
presentation:
  title: null
  use_fit_labels: true
  ratio_reference_label: HERAPDF2.0
  legend_fontsize: 13
```

The iteration configs set `presentation.title: HERAPDF2.0, NNLO, RTOPT`.
These conventions apply to individual panels as well as combined pages.

## Cross-section panels

The [HERAPDF2.0 low-Q² configuration](../runs/comparisons/xsec/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected-low-q2/config.yaml)
provides Figure 3: `HERA1+2 NCep 920` at Q² = 3.5 and 4.5 GeV², comparing
Gaussian with selected seven-source EoE. Its input files are:

```text
runs/fits/herapdf20-nnlo-rtopt/gaussian/output/fittedresults.txt
runs/fits/herapdf20-nnlo-rtopt/eoe-selected/output/fittedresults.txt
```

The bands come from these files' `therr+`/`therr-` columns. Optional
`Results.txt`, `minuit.out.txt`, `parsout_0` and `parsout_1` supply the renderer's
summary pages. Use the paper build for both runtime initialization and the
configured renderer:

```bash
workspace=runs/comparisons/xsec/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected-low-q2
XFITTER_TREE=merge-master/xfitter-master \
XFITTER_COMMIT=67398b15571dff1e9ddce0bc88923554552c9c84 \
  scripts/plot-xsec "$workspace"
```

The native `plots/xsec_comparison.pdf` has four 595 × 595 pt pages for these
inputs: the two cross-section slices followed by χ² and parameter summaries.
Figure 3 uses the first two pages. The auxiliary summaries have known display
limitations with these EoE outputs; use original fit `Results.txt` files for
numerical fit-quality statements.

Figure 3 retains the native ROOT text sizes and layout, `Gaussian` / `EoE`
legends, Q² units of GeV² and a `Theory/Data` ratio axis. Its configuration sets
`show_setup_annotation: false`, `therr: true` and `plots_per_page: 1`.

With Poppler installed:

```bash
pdfinfo "$workspace/plots/xsec_comparison.pdf"
pdftotext -f 1 -l 2 -layout "$workspace/plots/xsec_comparison.pdf" -
```

Check the page geometry, both Q² labels, legends and visible bands. The staging
report should contain 29 selected points per fit across these two slices.

## Auxiliary comparisons

The [selected BG versus resummed PDF comparison](../runs/comparisons/pdf/cross-setups/eoe-selected-bg-vs-resummed/config.yaml)
and [BG low-Q² cross-section comparison](../runs/comparisons/xsec/herapdf-bg-nnlo-rtopt/gaussian-vs-eoe-selected-low-q2/config.yaml)
use external auxiliary fit paths recorded explicitly in their configs. Their
regeneration requires those exact outputs. They are separate from the eight
comparison configurations used for the paper figures above.
Existing derived files alone do not establish input availability.
