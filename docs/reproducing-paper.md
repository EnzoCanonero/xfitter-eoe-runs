# Reproducing the paper results

[Repository](../README.md) · [Installation](installation.md) ·
[HERA application and catalog](hera-study.md)

The current paper campaign comprises **13 fixed-fit workspaces, 24 scan
configurations and 9 comparison configurations**. This guide maps those inputs
to Figures 1–7 and the main-text Tables 1–6. Configuration counts describe the
available studies; they do not certify that a local checkout contains completed
results.

The repository produces native figure pages, scan CSVs and a region table.
Final multi-panel manuscript assembly and a complete automated check of every
numerical statement are separate steps; there is no repository command that
builds the entire paper.

## Dependencies and order of work

Install the [Python and xFitter runtime](installation.md) and make the tracked
HERA datasets available. All paper fit launchers and the 24 paper scan
configurations select `merge-master/xfitter-master` at commit
`67398b15571dff1e9ddce0bc88923554552c9c84`. The resummed and matched fixed-order
FONLL-C fits require that build's APFEL 3.0.6/HELL 3 dependencies.

There are three input branches:

1. The [HERA fixed fits](hera-fits.md) provide Gaussian, selected EoE,
   informed EoE and iterative-profiling results for comparisons and numerical
   summaries. Their selected source lists are already specified.
2. The [23 forward-selection rounds](../runs/scans/forward-selection/README.md)
   establish the source rankings and stopping tests in Tables 1, 3 and 4.
   Reproducing only the fixed selected fits does not reproduce this selection
   evidence.
3. The [common-ε scan](../runs/scans/eoe-scan/README.md) supplies Figure 1.
   It refits the seven selected HERAPDF2.0 sources at eight ε values while
   keeping the source list fixed.

If outputs are missing, generate and submit the relevant workspaces using
their family guides, then validate their final fit and batch status. Fit
`condor/submit.sh` launchers submit immediately. For scans,
`python scripts/run-scan --dry-run WORKSPACE` only previews;
`--no-submit` writes inputs without submission; omitting both flags generates
and submits. Generation and fitting can reuse existing local paths, so keep a
separate workspace for changed scientific inputs.

When results already exist, proceed directly to extraction and plotting. The
commands below read fit outputs and write derived `results/` or `plots/`
files; they do not submit jobs. They replace existing derived files with the
same names.

## Figure map

All paths in this table are relative to `runs/`. The PDF comparisons use
Q² = 4 GeV² and the native xFitter central and Pumplin grids
(`source: xfitter-grid`). The plotting runtime still imports LHAPDF, but these
configurations do not require an external LHAPDF set for their curves.

| Figure | Workspace | Content |
| --- | --- | --- |
| 1 | [`scans/eoe-scan/herapdf20-nnlo-rtopt/common-epsilon`](../runs/scans/eoe-scan/herapdf20-nnlo-rtopt/common-epsilon/config.yaml) | Corrected minimum χ² versus common ε, with seven sources held selected |
| 2 | [`comparisons/pdf/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected`](../runs/comparisons/pdf/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected/config.yaml) | HERAPDF2.0, NNLO, RTOPT: Gaussian and selected EoE PDFs |
| 3 | [`comparisons/xsec/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected-low-q2`](../runs/comparisons/xsec/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected-low-q2/config.yaml) | NC e⁺p, 920 GeV: Q² = 3.5 and 4.5 GeV² |
| 4 | [`comparisons/pdf/herapdf-bg-nnlo-rtopt/gaussian-vs-eoe-selected`](../runs/comparisons/pdf/herapdf-bg-nnlo-rtopt/gaussian-vs-eoe-selected/config.yaml) | HERAPDF-BG, NNLO, RTOPT: Gaussian and selected EoE PDFs |
| 5 | [`comparisons/pdf/herapdf-bg-nnlo-nllx-fonll-c/gaussian-vs-eoe-selected`](../runs/comparisons/pdf/herapdf-bg-nnlo-nllx-fonll-c/gaussian-vs-eoe-selected/config.yaml) | HERAPDF-BG, NNLO+NLLₓ, FONLL-C: Gaussian and selected EoE PDFs |
| 6 | [`comparisons/pdf/cross-setups/eoe-informed`](../runs/comparisons/pdf/cross-setups/eoe-informed/config.yaml) | Three informed EoE setups, with ratios to HERAPDF2.0 |
| 7 | [`numerical-vs-iter02`](../runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter02/config.yaml), [`numerical-vs-iter04`](../runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter04/config.yaml), [`numerical-vs-iter08`](../runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter08/config.yaml) under `comparisons/pdf/herapdf20-nnlo-rtopt/` | Iterative nuisance profiling versus the numerical seven-source fit |

## Regenerate the native figure files

Run from the repository root after validating the input outputs.

```bash
# Figure 1
scripts/plot-scan runs/scans/eoe-scan/herapdf20-nnlo-rtopt/common-epsilon

# Figures 2, 4 and 5
scripts/plot-pdf-comparison runs/comparisons/pdf/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected
scripts/plot-pdf-comparison runs/comparisons/pdf/herapdf-bg-nnlo-rtopt/gaussian-vs-eoe-selected
scripts/plot-pdf-comparison runs/comparisons/pdf/herapdf-bg-nnlo-nllx-fonll-c/gaussian-vs-eoe-selected

# Figure 3
scripts/plot-xsec runs/comparisons/xsec/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected-low-q2

# Figure 6
scripts/plot-pdf-comparison runs/comparisons/pdf/cross-setups/eoe-informed

# Figure 7
scripts/plot-pdf-comparison runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter02
scripts/plot-pdf-comparison runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter04
scripts/plot-pdf-comparison runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter08
```

Figure 1 is `plots/1_chi2_vs_lambda.pdf` in its scan workspace. The internal
coordinate and filename remain `lambda`; the configuration sets base ε = 1,
so λ is the physical common ε. Its `paper-common-epsilon` style gives the
titleless manuscript plot. The other scan PDFs are diagnostics. The optional
`7_parameter_comparison.pdf` requires λ = 1, outside this scan's 0–0.7 grid,
and is skipped.

Each PDF comparison writes three multi-page files in its `plots/` directory:

- `pdf_comparison.pdf`: absolute and ratio panels together.
- `pdf_comparison_absolute.pdf`: absolute panels only.
- `pdf_comparison_ratio.pdf`: ratio panels only.

Pages follow the configuration's `observables` order. The manuscript uses
`uv`, `dv` and `gluon`; the HERAPDF2.0 configurations additionally produce a
`sea` page. The current labels and presentation settings also apply to the
individual absolute and ratio pages. Figure 3's native
`plots/xsec_comparison.pdf` contains four pages: the two configured cross-section
panels and two fit-summary pages, produced by `xfitter-draw` and ROOT.

These are the native inputs to manuscript assembly. Arranging the observable
pages into the final paper layouts is external to this repository; the plotting
commands do not create a numbered `figure-1.pdf`–`figure-7.pdf` bundle. See the
[PDF](../runs/comparisons/pdf/README.md) and
[cross-section](../runs/comparisons/xsec/README.md) guides for configuration and
output details.

## Table map and numerical checks

| Table | Inputs | What to check |
| --- | --- | --- |
| 1 | HERAPDF2.0 [forward-selection rounds 01–08](../runs/scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/) | Winning source, corrected minimum and marginal reduction; seven retained sources and stopping round |
| 2 | [HERAPDF2.0 region comparison](../runs/comparisons/regions/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected/config.yaml) | Change in pointwise data χ² and point counts by x and Q² region |
| 3 | BG RTOPT [rounds 01–09](../runs/scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/) | Eight retained sources and stopping round |
| 4 | BG resummed [rounds 01–06](../runs/scans/forward-selection/herapdf-bg-nnlo-nllx-fonll-c/epsilon-0p6/) | Five retained sources and stopping round |
| 5 | `gaussian` and `eoe-selected` fixed fits for the three selected setups, plus Tables 1/3/4 | Gaussian minima, final corrected minima and selected-source counts |
| 6 | `gaussian` and `eoe-informed` fixed fits for those three setups | Degrees of freedom, Gaussian minima and informed corrected minima |

### Forward-selection tables

Extract an existing round with, for example:

```bash
scripts/plot-scan runs/scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-01
```

Repeat for all rounds in the three chains. This command writes
`results/chi2.csv`, `results/parameters.csv` and `results/rankings.csv`, as
well as ranking and per-candidate parameter plots. The complete plotting step
can produce many diagnostic pages; the CLI has no extraction-only option.

Compare the extracted candidates with `runs/batch/fit_dirs.txt`. A round with
*k* sources already selected has 169 − *k* candidates plus its `nominal` base
fit. Missing outputs and non-converged fits require review: a sorted CSV alone
does not establish a valid winner. Inspect `non_converged` and
`base_converged` in `rankings.csv` and the final job output.

Use `dchi2_corrected`, the base's corrected minimum minus the candidate's
corrected minimum. Retain the best valid source when this improvement exceeds
1; the last round in each configured chain tests the stopping criterion.
Check that its winner extends the next round's `base_systematics` list.
The stored configurations contain the paper's prefixes and seeds explicitly;
the runner does not derive later rounds from earlier results or choose a new
selection automatically.

### Region table

```bash
scripts/plot-xsec runs/comparisons/regions/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected
```

This writes `results/region_table.csv` and `results/region_table.tex`.
The sign convention is selected minus Gaussian, so a negative value is an
improvement. The table sums squared pointwise pulls from `fittedresults.txt`.
It excludes nuisance constraints, the prediction-dependent logarithmic term
and the global Bartlett correction; its total is not the change in corrected
fit χ². See the [region-table guide](../runs/comparisons/regions/README.md).

### Fit summaries and nuisance parameters

Tables 5 and 6 do not have dedicated manuscript-table export commands. Their
inputs are the fixed-fit outputs listed above. Those outputs also provide
nuisance-parameter diagnostics, without a numbered manuscript-table exporter.
The existing
[`ResultsParser`](../src/xfitter_eoe_runs/scans/extract.py) exposes minimized
χ², degrees of freedom, Bartlett factors and the systematic-shift table. For
example, this reads a fit without writing files:

```bash
PYTHONPATH=src python - <<'PY'
from pathlib import Path
from xfitter_eoe_runs.scans.extract import ResultsParser

fit = Path("runs/fits/herapdf20-nnlo-rtopt/eoe-selected")
results = ResultsParser(fit)
print("raw chi2:", results.parse_chi2(), "ndof:", results.parse_ndf())
print("Bartlett factors:", results.parse_bartlett_factors())
print(results.parse_systematic_shifts().to_string(index=False))
PY
```

Use the goodness-of-fit Bartlett correction for corrected minima. Scan
extraction computes raw χ² times xFitter's printed χ² multiplier. Printed
precision can affect the last displayed hundredth; record any such difference
when comparing against `Corrected Chi2` or paper values. The confidence-interval
correction is a different factor.

For a comparison of nuisance shifts and conditional fixed-PDF errors, use the
`shift` and `error` columns for the selected sources. Keep these distinct from
`corr_err` and profiled PDF-parameter errors. Neither the parser example nor a
generated plot checks convergence by itself.

## Scope of the reproduction

The matched fixed-order `herapdf-bg-nnlo-fonll-c/gaussian` fit supports the
paper's comparison of theoretical treatments, although it is not a separate
curve in Figures 1–7. Keep it when checking the reported fit minima.

The active paper configurations use Q² ≥ 3.5 GeV². Statements about refits
with cuts at 2 or 10 GeV², or rerunning forward selection at other common ε
values, are not established by these configurations. The common-ε curve holds
the selected list fixed. Auxiliary λ scans, likelihood profiles and Pumplin
stability scans have their own settings and do not replace those missing
reselection or cut studies.

For a numerical claim, retain the source output, the statistic being compared,
its precision and the applicable convergence checks. Inspect the final native
pages for missing curves, bands and labels, then check the assembled manuscript
separately. Matching the visual layout alone does not validate a table or a
statement about the fit.
