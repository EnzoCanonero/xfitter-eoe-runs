# HERA reference fits

[HERA study and notation](hera-study.md) ·
[General fit workflow](../runs/fits/README.md) ·
[Installation](installation.md) · [Paper reproduction](reproducing-paper.md)

The supplied HERA application contains 13 fixed-fit workspaces. They fit the
combined inclusive data and provide the PDF bands, cross sections and fit
statistics used in the paper comparisons. An `eoe-selected` fit already
specifies its final source list; the separate
[forward-selection scans](../runs/scans/forward-selection/README.md) provide
the evidence for that selection.

## Setups and variants

All paths below are under `runs/fits/`. The
[HERA catalog](hera-study.md#fits) links the individual configurations.

| Setup directory | Variants | Physical setup |
| --- | --- | --- |
| [`herapdf20-nnlo-rtopt`](../runs/fits/herapdf20-nnlo-rtopt/) | `gaussian`, `eoe-selected`, `eoe-informed`, `eoe-selected-iter02`, `eoe-selected-iter04`, `eoe-selected-iter08` | HERAPDF2.0, NNLO, RTOPT |
| [`herapdf-bg-nnlo-rtopt`](../runs/fits/herapdf-bg-nnlo-rtopt/) | `gaussian`, `eoe-selected`, `eoe-informed` | HERAPDF-BG, NNLO, RTOPT |
| [`herapdf-bg-nnlo-fonll-c`](../runs/fits/herapdf-bg-nnlo-fonll-c/) | `gaussian` | HERAPDF-BG, NNLO, FONLL-C; matched fixed-order reference for the resummed setup |
| [`herapdf-bg-nnlo-nllx-fonll-c`](../runs/fits/herapdf-bg-nnlo-nllx-fonll-c/) | `gaussian`, `eoe-selected`, `eoe-informed` | HERAPDF-BG, NNLO+NLLₓ, FONLL-C |

The variant names distinguish the systematic treatment:

- `gaussian` uses the standard Gaussian constraints.
- `eoe-selected` assigns ε = 0.6 to the final selected sources: seven for
  HERAPDF2.0, eight for BG RTOPT and five for the resummed setup. All selected
  nuisance parameters are fitted numerically (`:E`).
- `eoe-informed` assigns ε = 0.6 to seven procedural sources and ε = 0.3 to
  forty HERA sources. The other sources retain Gaussian constraints. This
  assignment is specified independently of the forward-selection ranking.
- `eoe-selected-iter02/04/08` uses the same seven-source HERAPDF2.0 selection,
  with two nuisance parameters fitted numerically and five profiled using
  2, 4 or 8 iterations. The numerical reference is `eoe-selected`.

All 13 configurations use Pumplin errors with `ERRDEF = 0.5` and
`ITERATE = 10`. This error-calculation iteration count is separate from the
nuisance-profiling `n_iterations` in `steering.txt`.

## Inputs and tested build selection

The seven HERA inclusive data files are tracked in
[`datasets/hera/h1zeusCombined/inclusiveDis/1506.06042`](../datasets/hera/h1zeusCombined/inclusiveDis/1506.06042/).
These fits use Q² ≥ 3.5 GeV². Their tracked launchers restore missing dataset
copies into `config/` before submission. Workspace data copies, generated
workers, logs and fit outputs are ignored by Git.

All 13 launchers explicitly select `merge-master/xfitter-master` at commit
`67398b15571dff1e9ddce0bc88923554552c9c84` before sourcing
`scripts/setup-env.sh`. Changing the default build in `.env` does not retarget
those launchers. The FONLL-C configurations require the APFEL 3.0.6/HELL 3
dependency stack of that build. Follow [installation](installation.md) to
provide its paths and runtime.

The HERA launchers request one CPU and 2 GB for RTOPT, or 4 GB for FONLL-C.
They use the shared-filesystem Condor execution and CVMFS/OpenBLAS setup
described in the general installation guide.

## Reproduce a HERA fit

To preserve an existing result, create a separate workspace and copy the
chosen launcher's build pin and resource settings. Run from the repository
root:

```bash
scripts/new-fit \
  herapdf20-nnlo-rtopt/reproduction/gaussian \
  herapdf20-nnlo-rtopt/gaussian/config
cp runs/fits/herapdf20-nnlo-rtopt/gaussian/condor/submit.sh \
  runs/fits/herapdf20-nnlo-rtopt/reproduction/gaussian/condor/submit.sh
```

These commands create files without submitting. `new-fit` copies configuration
files, not the source launcher; the explicit copy preserves the HERA launch
settings. Review the copied inputs, then submit with:

```bash
bash runs/fits/herapdf20-nnlo-rtopt/reproduction/gaussian/condor/submit.sh
```

**This command submits a job.** It also creates the worker and descriptor and
patches the absolute output path. To run a different existing variant, use its
configuration and launcher in both copy steps. Running an existing workspace's
launcher directly reuses its output and log paths.

Without a template argument, `scripts/new-fit` currently defaults to the
HERAPDF2.0 Gaussian configuration. That default does not copy its explicit
build pin. The [general fit guide](../runs/fits/README.md) explains input
handling and runtime selection for new studies.

## Validate and compare

Apply the [fit-output checks](../runs/fits/README.md#expected-outputs-and-validation)
before interpreting a result. For the paper PDF comparisons, verify the
central grid at Q² = 4 GeV² and complete Pumplin plus/minus member pairs.
Cross-section comparisons use `output/fittedresults.txt`.

The [paper reproduction guide](reproducing-paper.md) maps these fixed fits to
the native figures and main numerical tables. Replotting existing results
does not require submitting another fit. The fixed-order FONLL-C Gaussian
workspace supports the reported comparison of theoretical treatments even
though it is not a separate curve in Figures 1–7.
