# HERA case study and configuration catalog

[Project overview](../README.md) · [Installation](installation.md) ·
[Paper reproduction](reproducing-paper.md)

The reusable commands are described in the [workspace guides](../runs/README.md).
This page records the HERA-specific setup names, uncertainty assignments and
configured workspaces. These choices are an application of the tools, not
restrictions on PDF-comparison scales or DIS cross-section panel selection.

Detailed examples: [HERA fits](hera-fits.md), [HERA scans](hera-scans.md),
[HERA comparisons](hera-comparisons.md). The [reproduction guide](reproducing-paper.md)
maps these products to the manuscript figures and main tables.

The bundled HERA application contains **13 fit workspaces, 30 scan configurations,
and 11 comparisons**. Paths identify the physical setup and study. This catalog
describes configured studies, not job completion.

Paper workspaces use the inputs of the 20260929 campaign. Auxiliary studies
retain their own inputs and build pins. The auxiliary PDF/cross-section
comparisons and likelihood profiles refer to external fit inputs under
`../xfitter-eoe-runs-archive/` (relative to the repository root); those inputs
are not included in a clone. The ε/λ and Pumplin scans generate their own fits.

Choose a guide for execution instructions, or use the configuration links below
to inspect an individual study.

| Study family | Usage guide |
| --- | --- |
| Standalone Gaussian and EoE fits | [Reference fits](../runs/fits/README.md) |
| Selection of EoE sources | [Forward selection](../runs/scans/forward-selection/README.md) |
| Common ε and λ dependence | [EoE scans](../runs/scans/eoe-scan/README.md) |
| Profiled χ² | [Likelihood profiles](../runs/scans/likelihood/README.md) |
| Uncertainty-calculation stability | [Pumplin stability](../runs/scans/pumplin-stability/README.md) |
| PDF central values and bands | [PDF comparisons](../runs/comparisons/pdf/README.md) |
| Reduced cross sections | [Cross-section comparisons](../runs/comparisons/xsec/README.md) |
| Data χ² by region | [Regional tables](../runs/comparisons/regions/README.md) |

| Setup slug | Physical setup |
| --- | --- |
| `herapdf20-nnlo-rtopt` | HERAPDF2.0, NNLO, RTOPT |
| `herapdf-bg-nnlo-rtopt` | HERAPDF-BG, NNLO, RTOPT |
| `herapdf-bg-nnlo-fonll-c` | HERAPDF-BG, NNLO, FONLL-C |
| `herapdf-bg-nnlo-nllx-fonll-c` | HERAPDF-BG, NNLO+NLLₓ, FONLL-C |

## Notation for this application

Each setup name specifies the PDF parametrisation, perturbative calculation and
heavy-quark scheme. The setup slugs above are the names used for this campaign;
new studies may use other descriptive names.

- `gaussian`: Gaussian nuisance-parameter constraints.
- `eoe-selected`: the final source set chosen by forward selection at ε = 0.6.
- `eoe-informed`: the separate a priori EoE assignment.
- `eoe-selected-iter02/04/08`: HERAPDF2.0 profiling variants with two numerical
  and five iteratively profiled selected nuisances.

Plot labels use the presentation recorded in each comparison configuration.
The [HERA comparison notes](hera-comparisons.md) document the manuscript's
headings, shortened labels, fonts and ratio references.

## Preview the supplied example

After [Python installation](installation.md), run from the repository root:

```bash
python scripts/run-scan --dry-run \
  runs/scans/eoe-scan/herapdf20-nnlo-rtopt/common-epsilon
```

This previews eight fits without generating files or submitting jobs. The
source list is fixed while ε runs from 0 to 0.7. Continue with the
[HERA scan examples](hera-scans.md) for execution and extraction.

## Fits

All 13 fits support the paper. Each workspace retains its `config/`, launchers,
and local outputs. `eoe-selected` denotes the final forward-selection fit;
`eoe-informed` denotes the separate informed assignment. The HERAPDF2.0
`iter02/04/08` fits profile five selected sources while fitting two numerically.

| Setup | Fit configurations |
| --- | --- |
| HERAPDF2.0 NNLO RTOPT (6) | [Gaussian](../runs/fits/herapdf20-nnlo-rtopt/gaussian/config/parameters.yaml), [selected EoE](../runs/fits/herapdf20-nnlo-rtopt/eoe-selected/config/parameters.yaml), [informed EoE](../runs/fits/herapdf20-nnlo-rtopt/eoe-informed/config/parameters.yaml), iterative [2](../runs/fits/herapdf20-nnlo-rtopt/eoe-selected-iter02/config/parameters.yaml), [4](../runs/fits/herapdf20-nnlo-rtopt/eoe-selected-iter04/config/parameters.yaml), [8](../runs/fits/herapdf20-nnlo-rtopt/eoe-selected-iter08/config/parameters.yaml) |
| HERAPDF-BG NNLO RTOPT (3) | [Gaussian](../runs/fits/herapdf-bg-nnlo-rtopt/gaussian/config/parameters.yaml), [selected EoE](../runs/fits/herapdf-bg-nnlo-rtopt/eoe-selected/config/parameters.yaml), [informed EoE](../runs/fits/herapdf-bg-nnlo-rtopt/eoe-informed/config/parameters.yaml) |
| HERAPDF-BG NNLO FONLL-C (1) | [Gaussian matched fixed-order reference](../runs/fits/herapdf-bg-nnlo-fonll-c/gaussian/config/parameters.yaml) |
| HERAPDF-BG NNLO+NLLₓ FONLL-C (3) | [Gaussian](../runs/fits/herapdf-bg-nnlo-nllx-fonll-c/gaussian/config/parameters.yaml), [selected EoE](../runs/fits/herapdf-bg-nnlo-nllx-fonll-c/eoe-selected/config/parameters.yaml), [informed EoE](../runs/fits/herapdf-bg-nnlo-nllx-fonll-c/eoe-informed/config/parameters.yaml) |

All 13 fit launchers pin `merge-master/xfitter-master` at
`67398b15571dff1e9ddce0bc88923554552c9c84`. The FONLL-C fits require its
APFEL 3.0.6/HELL 3 dependencies; the fixed-order reference and resummed Gaussian
fit use matched settings. See the [environment instructions](installation.md#scientific-runtime).
`scripts/new-fit` defaults to `fits/herapdf20-nnlo-rtopt/gaussian/config`.

## Scans

There are **24 paper configurations and 6 auxiliary configurations**. The
forward-selection chains use ε = 0.6 and a Q² cut of 3.5 GeV². Round 01 starts
with no sources selected; the final round tests the stopping criterion. The selected
sources and seeds remain explicit in each configuration.

| Role | Study | Configuration links |
| --- | --- | --- |
| Paper | HERAPDF2.0 forward selection: 7 retained sources + stopping round | [01](../runs/scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-01/config.yaml), [02](../runs/scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-02/config.yaml), [03](../runs/scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-03/config.yaml), [04](../runs/scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-04/config.yaml), [05](../runs/scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-05/config.yaml), [06](../runs/scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-06/config.yaml), [07](../runs/scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-07/config.yaml), [08](../runs/scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-08/config.yaml) |
| Paper | HERAPDF-BG NNLO RTOPT forward selection: 8 retained sources + stopping round | [01](../runs/scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-01/config.yaml), [02](../runs/scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-02/config.yaml), [03](../runs/scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-03/config.yaml), [04](../runs/scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-04/config.yaml), [05](../runs/scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-05/config.yaml), [06](../runs/scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-06/config.yaml), [07](../runs/scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-07/config.yaml), [08](../runs/scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-08/config.yaml), [09](../runs/scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-09/config.yaml) |
| Paper | HERAPDF-BG NNLO+NLLₓ FONLL-C forward selection: 5 retained sources + stopping round | [01](../runs/scans/forward-selection/herapdf-bg-nnlo-nllx-fonll-c/epsilon-0p6/round-01/config.yaml), [02](../runs/scans/forward-selection/herapdf-bg-nnlo-nllx-fonll-c/epsilon-0p6/round-02/config.yaml), [03](../runs/scans/forward-selection/herapdf-bg-nnlo-nllx-fonll-c/epsilon-0p6/round-03/config.yaml), [04](../runs/scans/forward-selection/herapdf-bg-nnlo-nllx-fonll-c/epsilon-0p6/round-04/config.yaml), [05](../runs/scans/forward-selection/herapdf-bg-nnlo-nllx-fonll-c/epsilon-0p6/round-05/config.yaml), [06](../runs/scans/forward-selection/herapdf-bg-nnlo-nllx-fonll-c/epsilon-0p6/round-06/config.yaml) |
| Paper | HERAPDF2.0 common ε, 0–0.7, with the seven selected sources fixed (Figure 1) | [Common epsilon](../runs/scans/eoe-scan/herapdf20-nnlo-rtopt/common-epsilon/config.yaml) |
| Auxiliary | Fixed-selection λ scaling, ε = 0.6λ | [HERAPDF2.0](../runs/scans/eoe-scan/herapdf20-nnlo-rtopt/lambda-scaling/config.yaml), [HERAPDF-BG RTOPT](../runs/scans/eoe-scan/herapdf-bg-nnlo-rtopt/lambda-scaling/config.yaml), [HERAPDF-BG resummed](../runs/scans/eoe-scan/herapdf-bg-nnlo-nllx-fonll-c/lambda-scaling/config.yaml) |
| Auxiliary | HERAPDF2.0 likelihood profiles: 14 PDF parameters; selected EoE also profiles 7 NPs | [Gaussian](../runs/scans/likelihood/herapdf20-nnlo-rtopt/gaussian/config.yaml), [selected EoE](../runs/scans/likelihood/herapdf20-nnlo-rtopt/eoe-selected/config.yaml) |
| Auxiliary | Pumplin stability under λ, ERRDEF and ITERATE variations | [Selected EoE](../runs/scans/pumplin-stability/herapdf20-nnlo-rtopt/eoe-selected/config.yaml) |

The common-ε and λ scans hold their source lists fixed; they are distinct from
repeating forward selection at each ε. Likelihood profiles require the configured
reference fit's `output/minuit.out.txt`.

## Comparisons

There are **9 paper configurations and 2 auxiliary configurations**. These
consume existing fitted results. The [HERA comparison notes](hera-comparisons.md)
document the campaign's labels, fonts and native figure files; the
[PDF comparison guide](../runs/comparisons/pdf/README.md) describes the general interface.

| Role | Study | Configuration links |
| --- | --- | --- |
| Paper | Gaussian vs selected EoE PDFs (Figures 2, 4, 5) | [HERAPDF2.0](../runs/comparisons/pdf/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected/config.yaml), [HERAPDF-BG RTOPT](../runs/comparisons/pdf/herapdf-bg-nnlo-rtopt/gaussian-vs-eoe-selected/config.yaml), [HERAPDF-BG resummed](../runs/comparisons/pdf/herapdf-bg-nnlo-nllx-fonll-c/gaussian-vs-eoe-selected/config.yaml) |
| Paper | Numerical vs iterative HERAPDF2.0 profiling (Figure 7) | [2 iterations](../runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter02/config.yaml), [4 iterations](../runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter04/config.yaml), [8 iterations](../runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter08/config.yaml) |
| Paper | Three informed PDF setups (Figure 6) | [Informed comparison](../runs/comparisons/pdf/cross-setups/eoe-informed/config.yaml) |
| Paper | HERAPDF2.0 NC e⁺p cross sections at Q² = 3.5 and 4.5 GeV² (Figure 3) | [Low-Q² comparison](../runs/comparisons/xsec/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected-low-q2/config.yaml) |
| Paper | HERAPDF2.0 change in data χ² by x and Q² region (Table 2) | [Region table](../runs/comparisons/regions/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected/config.yaml) |
| Auxiliary | Selected EoE PDFs: HERAPDF-BG RTOPT vs resummed | [Cross-setup comparison](../runs/comparisons/pdf/cross-setups/eoe-selected-bg-vs-resummed/config.yaml) |
| Auxiliary | HERAPDF-BG Gaussian/EoE low-Q² cross sections | [Low-Q² comparison](../runs/comparisons/xsec/herapdf-bg-nnlo-rtopt/gaussian-vs-eoe-selected-low-q2/config.yaml) |
