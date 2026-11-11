# HERA scan configurations and examples

[Repository](../README.md) · [HERA study](hera-study.md) ·
[Configuration catalog](../runs/README.md) · [Installation](installation.md) ·
[Paper reproduction](reproducing-paper.md)

This page describes the HERA studies supplied with the repository and provides
concrete workspace examples. The family READMEs document the general scan
interfaces. Counts below describe configurations and requested fits, not the
completion state of a local checkout.

All 30 scan configurations use the seven
[HERA inclusive dataset files](../datasets/hera/h1zeusCombined/inclusiveDis/1506.06042/)
with Q² ≥ 3.5 GeV², `enable_bartlett: true` and `n_iterations: 2`.
The last setting is the nuisance-profiling steering option, separate from
Pumplin's uncertainty-calculation `ITERATE` setting.

Each configuration explicitly sets `dataset_root` to the bundled
`datasets/hera/h1zeusCombined/inclusiveDis/1506.06042` directory, using a path
relative to its own `config.yaml`. For example, the common-ε workspace uses:

```yaml
dataset_root: ../../../../../datasets/hera/h1zeusCombined/inclusiveDis/1506.06042
```

## Forward selection

Tool documentation: [systematic-source ranking](../runs/scans/forward-selection/README.md).

The paper chains test EoE assignments at ε = 0.6. Each starts from 169 correlated
systematic sources; sources already in the base are excluded from the remaining
candidates. The last round tests the stopping criterion.

| Physical setup | Configurations | Final selected base | Template |
| --- | --- | --- | --- |
| HERAPDF2.0, NNLO, RTOPT | [8 rounds](../runs/scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/), [01](../runs/scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-01/config.yaml)–[08](../runs/scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-08/config.yaml) | 7 sources | `hera-baseline` |
| HERAPDF-BG, NNLO, RTOPT | [9 rounds](../runs/scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/), [01](../runs/scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-01/config.yaml)–[09](../runs/scans/forward-selection/herapdf-bg-nnlo-rtopt/epsilon-0p6/round-09/config.yaml) | 8 sources | `giuli-param` |
| HERAPDF-BG, NNLO+NLLₓ, FONLL-C | [6 rounds](../runs/scans/forward-selection/herapdf-bg-nnlo-nllx-fonll-c/epsilon-0p6/), [01](../runs/scans/forward-selection/herapdf-bg-nnlo-nllx-fonll-c/epsilon-0p6/round-01/config.yaml)–[06](../runs/scans/forward-selection/herapdf-bg-nnlo-nllx-fonll-c/epsilon-0p6/round-06/config.yaml) | 5 sources | `bg-param-nnlo-nllx-fonll` |

These **23 round configurations** record the paper's source lists and starting
values explicitly. Each can be replayed independently: generation does not read
the preceding round's outputs. This replay does not make a new adaptive
selection. For a new selection, inspect each ranking and prepare the next
configuration with the winning source and updated joint starting values.

The paper retains the best valid candidate when
`dchi2_corrected = chi2_corrected(base) - chi2_corrected(base + candidate)`
exceeds 1. Both endpoints use their own Bartlett corrections. The runner does
not enforce that threshold or choose the next round. With *k* base sources,
expect `170 − k` fits including `nominal`; round 01 therefore requests 170.
Check both candidate and base convergence before interpreting an improvement.

A concrete workspace for the command sequence below is:

```bash
workspace=runs/scans/forward-selection/herapdf20-nnlo-rtopt/epsilon-0p6/round-01
```

These scans provide the ranking evidence for the paper's selection tables.
Running only the final fixed selected fits does not reproduce that evidence.

## EoE-strength scans

Tool documentation: [EoE-strength scans](../runs/scans/eoe-scan/README.md).

The runner multiplies each source's ε by λ. All sources in these four
configurations scale together, and their lists remain fixed across the grid.
PDFs and nuisance shifts are refitted at every point; starting shifts in the
configuration are not fixed parameters.

| Role and physical setup | Configuration | Coordinate and requested fits |
| --- | --- | --- |
| Paper Figure 1: HERAPDF2.0, NNLO, RTOPT | [Common ε](../runs/scans/eoe-scan/herapdf20-nnlo-rtopt/common-epsilon/config.yaml) | Base ε = 1; λ is physical ε, 0–0.7 in steps of 0.1: **8 fits** |
| Auxiliary: HERAPDF2.0, NNLO, RTOPT | [λ scaling](../runs/scans/eoe-scan/herapdf20-nnlo-rtopt/lambda-scaling/config.yaml) | Physical ε = 0.6λ, λ = 0–1.2 in steps of 0.1: **13 fits** |
| Auxiliary: HERAPDF-BG, NNLO, RTOPT | [λ scaling](../runs/scans/eoe-scan/herapdf-bg-nnlo-rtopt/lambda-scaling/config.yaml) | Same λ grid: **13 fits** |
| Auxiliary: HERAPDF-BG, NNLO+NLLₓ, FONLL-C | [λ scaling](../runs/scans/eoe-scan/herapdf-bg-nnlo-nllx-fonll-c/lambda-scaling/config.yaml) | Same λ grid: **13 fits** |

The HERAPDF2.0, BG RTOPT and resummed lists contain 7, 8 and 5 sources,
respectively. At λ = 0 the scaled constraints are Gaussian while their source
declarations remain present. In the auxiliary scans, λ = 1 corresponds to
ε = 0.6 and λ = 1.2 to ε = 0.72. These curves do not repeat forward selection
at different ε values.

All four configurations use Pumplin with `ERRDEF = 0.5` and `ITERATE = 10`.
They generate their own fits from templates and tracked data; no external
reference-fit output is required. The templates follow the setup mapping in
the forward-selection table above. Build selections and some seeds differ
between the paper and auxiliary scans, so equal ε alone does not make their
fit points interchangeable.

Their `parameter_comparison` lists preserve the HERA plotting order and
notation: `Bg`, `Cg`, `Agp`, `Bgp`, `Buv`, `Cuv`, `Euv`, `Bdv`, `Cdv`, `CUbar`,
`DUbar`, `ADbar`, `BDbar`, `CDbar`. These names and labels are study settings
in each YAML file. If a selected name is absent from either endpoint, the
optional comparison is skipped.

For the Figure 1 study, use:

```bash
workspace=runs/scans/eoe-scan/herapdf20-nnlo-rtopt/common-epsilon
```

Its `plot_style: paper-common-epsilon` displays physical ε on the horizontal
axis. The native Figure 1 file is `plots/1_chi2_vs_lambda.pdf`; directory names
and CSV columns retain `lambda`. The other plots are diagnostics. The optional
`7_parameter_comparison.pdf` requires all configured parameters at both
λ = 0 and 1, so it is skipped for this 0–0.7 grid.

## Likelihood profiles

Tool documentation: [profile-likelihood scans](../runs/scans/likelihood/README.md).

| Reference | Configuration | Requested grid |
| --- | --- | --- |
| Gaussian HERAPDF2.0 | [Gaussian profiles](../runs/scans/likelihood/herapdf20-nnlo-rtopt/gaussian/config.yaml) | 14 PDF parameters × 31 points = **434 fits** |
| Seven-source HERAPDF2.0 EoE, ε = 0.6 | [PDF and nuisance profiles](../runs/scans/likelihood/herapdf20-nnlo-rtopt/eoe-selected/config.yaml) | 14 PDF + 7 nuisance parameters × 21 points = **441 fits** |

Both configurations request one-dimensional profiles over the reference value
±3 reference errors using `hera-baseline`. They are auxiliary diagnostics,
not a separately configured paper figure. Parameters absent from the reference
can be skipped; verify the generated manifest against the requested counts.

The `reference_fit` entries name inputs in the sibling
`xfitter-eoe-runs-archive/` directory. Provide the exact configured reference's
`output/minuit.out.txt` and retain `config/steering.txt` for the nuisance-source
order. A dry run also needs these inputs. The scans do not create the reference
fit and should not be silently redirected to newer fixed-fit outputs.

After making the reference available, use, for example:

```bash
workspace=runs/scans/likelihood/herapdf20-nnlo-rtopt/gaussian
```

The derived outputs are `results/profiles_1d.csv` and `plots/profiles_1d.pdf`.
Δχ² is based on the raw minimized statistic, not the Bartlett-corrected
goodness-of-fit value used for source rankings. The general guide describes
normalization and missing-point handling.

## Pumplin stability

Tool documentation: [Pumplin stability](../runs/scans/pumplin-stability/README.md).

The [configured grid](../runs/scans/pumplin-stability/herapdf20-nnlo-rtopt/eoe-selected/config.yaml)
uses the seven-source HERAPDF2.0 selection with `hera-baseline`:

| Setting | Values |
| --- | --- |
| λ | 0.5 and 1.0, plus the automatic Gaussian λ = 0 group |
| Physical EoE strength | ε = 0.6λ: 0.3 and 0.6 in the two EoE groups |
| Pumplin `ERRDEF` | 0.5 and 1.0 |
| Pumplin `ITERATE` | 10 and 20 |
| Plot reference `ERRDEF` | 0.5 |

There are **3 × 2 × 2 = 12 requested fits**. The Gaussian group has no EoE source
declarations; the others retain the seven sources and refit their shifts.
No reference-fit output is needed. This is an uncertainty-calculation test,
separate from the paper's 2/4/8 nuisance-profiling-iteration comparison.

The configuration selects the PDF diagnostics explicitly:

```yaml
plot_parameters:
  - ADbar
  - Agp
  - BDbar
  - Bdv
  - Bg
  - Bgp
  - Buv
  - CDbar
  - CUbar
  - Cdv
  - Cg
  - Cuv
  - DUbar
  - Euv
```

The seven configured E-type nuisance parameters are appended automatically.

Use:

```bash
workspace=runs/scans/pumplin-stability/herapdf20-nnlo-rtopt/eoe-selected
```

The main outputs are `results/pumplin_widths.csv`,
`plots/pumplin_iteration_convergence.pdf` and
`plots/pumplin_errdef_invariance.pdf`, with conditional eigenmode diagnostics.
For a complete grid, the iteration reference is 20 and the `ERRDEF` reference
is 0.5. Verify all 12 combinations and the references actually reported by the
plotter; missing results can change the available normalization points.

## Required builds

| Studies | Build directory | Commit |
| --- | --- | --- |
| All 23 forward-selection rounds and the common-ε scan | `merge-master/xfitter-master` | `67398b15571dff1e9ddce0bc88923554552c9c84` |
| HERAPDF2.0 and BG RTOPT auxiliary λ scans; both likelihood profiles; Pumplin grid | `xfitter-master` | `bd0470d93a433ebfb5d99f6c0fecda9c29141199` |
| Resummed auxiliary λ scan | `xfitter-bartlett-apfel306-hell3` | No `xfitter_commit` pin in this configuration |

The resummed setup requires its APFEL/HELL dependencies. Follow the
[installation guide](installation.md) and retain the worker's executable/library
provenance; changing `.env` does not replace a configuration's build selection.

## Commands for a chosen HERA workspace

Run from the repository root after installation. First execute **one** of the
concrete `workspace=...` assignments above, or choose a workspace from its
configuration table. For likelihood scans, prepare the reference inputs first.

Preview without creating files or submitting jobs:

```bash
python scripts/run-scan --dry-run "${workspace:?Choose a HERA workspace above}"
```

Generate inputs and batch files without submission:

```bash
python scripts/run-scan --no-submit "${workspace:?Choose a HERA workspace above}"
wc -l "$workspace/runs/batch/fit_dirs.txt"
```

Submit the generated batch when ready:

```bash
bash "${workspace:?Choose a HERA workspace above}/runs/submit.sh"
```

After the fits finish, extract and plot:

```bash
scripts/plot-scan "${workspace:?Choose a HERA workspace above}"
```

If fit outputs already exist, only the final command is needed. Generation
writes the chosen workspace's `runs/` tree; keep changed inputs in a separate
workspace. Compare extracted rows with the generated inventory and review
final fit and batch status. Plot existence alone does not establish completion.
The family guides describe exact outputs and the relevant checks.
