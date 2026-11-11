# Run catalog

The current tree contains **13 fit workspaces, 30 scan configurations, and
11 comparisons**. Paths identify the physical setup and study; their original
campaign identities and relocation history are recorded in the
[migration manifest](migration-20261111.json) and
[archive inventory](../legacy-artifacts.yaml). This catalog describes configured
studies, not job completion.

Paper workspaces retain the inputs of the 20260929 campaign. Auxiliary studies
retain their own inputs and build pins, including references to archived fits.
Moving a workspace does not replace its fitted results with a newer campaign.
Superseded workspaces and their products are retained locally under
`legacy/cleanup-20261111/`; that ignored archive is absent from fresh clones.
Nested `output_OLD/` backups and historical plot folders are archived there too;
their exact destinations are recorded in the archive's `artifact-moves.json`.
Plotting and scan commands accept workspaces under `runs/`; an archived study
must be restored there with its recorded inputs before those commands can run it.

| Setup slug | Physical setup |
| --- | --- |
| `herapdf20-nnlo-rtopt` | HERAPDF2.0, NNLO, RTOPT |
| `herapdf-bg-nnlo-rtopt` | HERAPDF-BG, NNLO, RTOPT |
| `herapdf-bg-nnlo-fonll-c` | HERAPDF-BG, NNLO, FONLL-C |
| `herapdf-bg-nnlo-nllx-fonll-c` | HERAPDF-BG, NNLO+NLLₓ, FONLL-C |

## Fits

All 13 fits support the paper. Each workspace retains its `config/`, launchers,
and local outputs. `eoe-selected` denotes the final forward-selection fit;
`eoe-informed` denotes the separate informed assignment. The HERAPDF2.0
`iter02/04/08` fits profile five selected sources while fitting two numerically.

| Setup | Fit configurations |
| --- | --- |
| HERAPDF2.0 NNLO RTOPT (6) | [Gaussian](fits/herapdf20-nnlo-rtopt/gaussian/config/parameters.yaml), [selected EoE](fits/herapdf20-nnlo-rtopt/eoe-selected/config/parameters.yaml), [informed EoE](fits/herapdf20-nnlo-rtopt/eoe-informed/config/parameters.yaml), iterative [2](fits/herapdf20-nnlo-rtopt/eoe-selected-iter02/config/parameters.yaml), [4](fits/herapdf20-nnlo-rtopt/eoe-selected-iter04/config/parameters.yaml), [8](fits/herapdf20-nnlo-rtopt/eoe-selected-iter08/config/parameters.yaml) |
| HERAPDF-BG NNLO RTOPT (3) | [Gaussian](fits/herapdf-bg-nnlo-rtopt/gaussian/config/parameters.yaml), [selected EoE](fits/herapdf-bg-nnlo-rtopt/eoe-selected/config/parameters.yaml), [informed EoE](fits/herapdf-bg-nnlo-rtopt/eoe-informed/config/parameters.yaml) |
| HERAPDF-BG NNLO FONLL-C (1) | [Gaussian matched fixed-order reference](fits/herapdf-bg-nnlo-fonll-c/gaussian/config/parameters.yaml) |
| HERAPDF-BG NNLO+NLLₓ FONLL-C (3) | [Gaussian](fits/herapdf-bg-nnlo-nllx-fonll-c/gaussian/config/parameters.yaml), [selected EoE](fits/herapdf-bg-nnlo-nllx-fonll-c/eoe-selected/config/parameters.yaml), [informed EoE](fits/herapdf-bg-nnlo-nllx-fonll-c/eoe-informed/config/parameters.yaml) |

All 13 fit launchers pin `merge-master/xfitter-master` at
`67398b15571dff1e9ddce0bc88923554552c9c84`. The FONLL-C fits require its
APFEL 3.0.6/HELL 3 dependencies; the fixed-order reference and resummed Gaussian
fit use matched settings. See the root [environment instructions](../README.md#setup).
`scripts/new-fit` defaults to `fits/herapdf20-nnlo-rtopt/gaussian/config`.

## Scans

There are **24 paper configurations and 6 auxiliary configurations**. The
forward-selection chains use ε = 0.6 and a Q² cut of 3.5 GeV². Round 01 starts
with no sources selected; the final round tests the stopping criterion. The selected
sources and seeds remain explicit in each configuration.

| Role | Study | Configuration links |
| --- | --- | --- |
| Paper | HERAPDF2.0 forward selection: 7 retained sources + stopping round | [01](scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-01/config.yaml), [02](scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-02/config.yaml), [03](scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-03/config.yaml), [04](scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-04/config.yaml), [05](scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-05/config.yaml), [06](scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-06/config.yaml), [07](scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-07/config.yaml), [08](scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-08/config.yaml) |
| Paper | HERAPDF-BG NNLO RTOPT forward selection: 8 retained sources + stopping round | [01](scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-01/config.yaml), [02](scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-02/config.yaml), [03](scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-03/config.yaml), [04](scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-04/config.yaml), [05](scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-05/config.yaml), [06](scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-06/config.yaml), [07](scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-07/config.yaml), [08](scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-08/config.yaml), [09](scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-09/config.yaml) |
| Paper | HERAPDF-BG NNLO+NLLₓ FONLL-C forward selection: 5 retained sources + stopping round | [01](scans/forward-selection/herapdf-bg-nnlo-nllx-fonll-c/epsilon-0p6/round-01/config.yaml), [02](scans/forward-selection/herapdf-bg-nnlo-nllx-fonll-c/epsilon-0p6/round-02/config.yaml), [03](scans/forward-selection/herapdf-bg-nnlo-nllx-fonll-c/epsilon-0p6/round-03/config.yaml), [04](scans/forward-selection/herapdf-bg-nnlo-nllx-fonll-c/epsilon-0p6/round-04/config.yaml), [05](scans/forward-selection/herapdf-bg-nnlo-nllx-fonll-c/epsilon-0p6/round-05/config.yaml), [06](scans/forward-selection/herapdf-bg-nnlo-nllx-fonll-c/epsilon-0p6/round-06/config.yaml) |
| Paper | HERAPDF2.0 common ε, 0–0.7, with the seven selected sources fixed (Figure 1) | [Common epsilon](scans/eoe-scan/herapdf20-nnlo-rtopt/common-epsilon/config.yaml) |
| Auxiliary | Fixed-selection λ scaling, ε = 0.6λ | [HERAPDF2.0](scans/eoe-scan/herapdf20-nnlo-rtopt/lambda-scaling/config.yaml), [HERAPDF-BG RTOPT](scans/eoe-scan/herapdf-bg-nnlo-rtopt/lambda-scaling/config.yaml), [HERAPDF-BG resummed](scans/eoe-scan/herapdf-bg-nnlo-nllx-fonll-c/lambda-scaling/config.yaml) |
| Auxiliary | HERAPDF2.0 likelihood profiles: 14 PDF parameters; selected EoE also profiles 7 NPs | [Gaussian](scans/likelihood/herapdf20-nnlo-rtopt/gaussian/config.yaml), [selected EoE](scans/likelihood/herapdf20-nnlo-rtopt/eoe-selected/config.yaml) |
| Auxiliary | Pumplin stability under λ, ERRDEF and ITERATE variations | [Selected EoE](scans/pumplin-stability/herapdf20-nnlo-rtopt/eoe-selected/config.yaml) |

The common-ε and λ scans hold their source lists fixed; they are distinct from
repeating forward selection at each ε. Auxiliary likelihood references retain
their original archived fit identity and require the corresponding local
`output/minuit.out.txt`.

## Comparisons

There are **9 paper configurations and 2 auxiliary configurations**. These
consume existing fitted results. The [paper presentation guide](../README.md#current-paper-plots-and-individual-panels)
documents labels, fonts, and the combined, absolute-only and ratio-only PDFs.

| Role | Study | Configuration links |
| --- | --- | --- |
| Paper | Gaussian vs selected EoE PDFs (Figures 2, 4, 5) | [HERAPDF2.0](comparisons/pdf/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected/config.yaml), [HERAPDF-BG RTOPT](comparisons/pdf/herapdf-bg-nnlo-rtopt/gaussian-vs-eoe-selected/config.yaml), [HERAPDF-BG resummed](comparisons/pdf/herapdf-bg-nnlo-nllx-fonll-c/gaussian-vs-eoe-selected/config.yaml) |
| Paper | Numerical vs iterative HERAPDF2.0 profiling (Figure 7) | [2 iterations](comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter02/config.yaml), [4 iterations](comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter04/config.yaml), [8 iterations](comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter08/config.yaml) |
| Paper | Three informed PDF setups (Figure 6) | [Informed comparison](comparisons/pdf/cross-setups/eoe-informed/config.yaml) |
| Paper | HERAPDF2.0 NC e⁺p cross sections at Q² = 3.5 and 4.5 GeV² (Figure 3) | [Low-Q² comparison](comparisons/xsec/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected-low-q2/config.yaml) |
| Paper | HERAPDF2.0 change in data χ² by x and Q² region (Table 2) | [Region table](comparisons/regions/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected/config.yaml) |
| Auxiliary | Selected EoE PDFs: HERAPDF-BG RTOPT vs resummed | [Cross-setup comparison](comparisons/pdf/cross-setups/eoe-selected-bg-vs-resummed/config.yaml) |
| Auxiliary | HERAPDF-BG Gaussian/EoE low-Q² cross sections | [Low-Q² comparison](comparisons/xsec/herapdf-bg-nnlo-rtopt/gaussian-vs-eoe-selected-low-q2/config.yaml) |

Auxiliary comparisons preserve their historical input paths and available
products. Moving them does not supply missing archived grids or make them
equivalent to the current paper fits.
