# HERA and paper figures

[Repository](../README.md) · [Installation](installation.md) ·
[Workflow guides](../runs/README.md)

This guide reproduces the figures in *Impact of errors-on-errors on the PDF
determination from combined HERA data*. The study compares Gaussian fits with
errors-on-errors (EoE) treatments of the combined HERA inclusive DIS data.
`eoe-selected` uses sources chosen by forward selection; `eoe-informed` uses
an assignment specified in advance.

Run commands from the repository root after [installation](installation.md).
Plotting requires completed fits: each comparison's `config.yaml` lists its
inputs. If they are missing, run those workspaces using the
[fit guide](../runs/fits/README.md). The supplied launchers select xFitter
master; to use yours, see
[using your own build](../runs/fits/README.md#use-your-own-xfitter-build).
Figure 1 uses its own
[EoE scan](../runs/scans/eoe-scan/README.md).

## Figure 1: Common epsilon

Bartlett-corrected minimum χ² as the common ε varies from 0 to 0.7, keeping
the seven selected HERAPDF2.0 sources fixed.
[Configuration](../runs/scans/eoe-scan/herapdf20-nnlo-rtopt/common-epsilon/config.yaml).

```bash
workspace=runs/scans/eoe-scan/herapdf20-nnlo-rtopt/common-epsilon
python scripts/run-scan --dry-run "$workspace"  # preview the eight fits
# After running the scan:
scripts/plot-scan "$workspace"
```

The figure is `plots/1_chi2_vs_lambda.pdf` within this workspace.

## Figure 2: HERAPDF2.0 PDFs

Gaussian versus selected EoE PDFs for HERAPDF2.0, NNLO, RTOPT at Q² = 4 GeV².
[Configuration](../runs/comparisons/pdf/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected/config.yaml).

```bash
scripts/plot-pdf-comparison runs/comparisons/pdf/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected
```

## Figure 3: Low-Q2 cross sections

Gaussian versus selected EoE predictions for NC e⁺p at a proton energy of
920 GeV, at Q² = 3.5 and 4.5 GeV².
[Configuration](../runs/comparisons/xsec/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected-low-q2/config.yaml).

```bash
scripts/plot-xsec runs/comparisons/xsec/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected-low-q2
```

Use the first two pages of `plots/xsec_comparison.pdf` in this workspace.

## Figure 4: HERAPDF-BG PDFs

Gaussian versus selected EoE PDFs with the more flexible HERAPDF-BG
parametrisation, at NNLO with RTOPT and Q² = 4 GeV².
[Configuration](../runs/comparisons/pdf/herapdf-bg-nnlo-rtopt/gaussian-vs-eoe-selected/config.yaml).

```bash
scripts/plot-pdf-comparison runs/comparisons/pdf/herapdf-bg-nnlo-rtopt/gaussian-vs-eoe-selected
```

## Figure 5: Resummed HERAPDF-BG PDFs

Gaussian versus selected EoE PDFs for HERAPDF-BG with NNLO+NLLₓ resummation
and FONLL-C, at Q² = 4 GeV².
[Configuration](../runs/comparisons/pdf/herapdf-bg-nnlo-nllx-fonll-c/gaussian-vs-eoe-selected/config.yaml).

```bash
scripts/plot-pdf-comparison runs/comparisons/pdf/herapdf-bg-nnlo-nllx-fonll-c/gaussian-vs-eoe-selected
```

## Figure 6: Informed EoE

The three PDF setups with the same informed EoE assignment, at Q² = 4 GeV².
Ratios use the informed HERAPDF2.0 fit as the reference.
[Configuration](../runs/comparisons/pdf/cross-setups/eoe-informed/config.yaml).

```bash
scripts/plot-pdf-comparison runs/comparisons/pdf/cross-setups/eoe-informed
```

## Figure 7: Iterative profiling

PDF ratios after 2, 4 and 8 nuisance-profiling iterations, relative to the
HERAPDF2.0 fit with all seven selected sources minimized numerically.
Configurations: [2](../runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter02/config.yaml),
[4](../runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter04/config.yaml),
[8 iterations](../runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter08/config.yaml).

```bash
for iterations in 02 04 08; do
  scripts/plot-pdf-comparison "runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter${iterations}"
done
```

For Figures 2, 4, 5 and 6, use the `uv`, `dv` and `gluon` pages from each
workspace's `plots/pdf_comparison_absolute.pdf` and `pdf_comparison_ratio.pdf`.
Figure 7 uses the ratio pages only. Arrange these panels into the paper layout
separately; the commands produce the individual pages.
