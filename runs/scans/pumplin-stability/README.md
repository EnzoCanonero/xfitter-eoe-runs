# Pumplin uncertainty stability

[Repository](../../../README.md) · [Installation](../../../docs/installation.md) ·
[HERA study](../../../docs/hera-study.md) ·
[HERA example](../../../docs/hera-scans.md#pumplin-stability) ·
[Paper reproduction](../../../docs/reproducing-paper.md)

`scan_type: pumplin-stability` varies EoE strengths and the Pumplin `ERRDEF`
and `ITERATE` settings. It compares interval estimates and, when available,
covariance-mode contributions. Pumplin `ITERATE` controls the uncertainty
calculation; it is separate from the steering's nuisance-profiling
`n_iterations` setting.

## Configuration and inputs

Create a `config.yaml` in a workspace under `runs/scans/`.

| Field | Meaning |
| --- | --- |
| `scan_type` | `pumplin-stability` |
| `template`, `datafiles` | Named root template and dataset filenames |
| `eps` | Default source strength before multiplying by λ |
| `systematics` | Source entries with `name`, `type`, optional `epsilon`, `init` and numbered `range` |
| `lambda` | List of EoE scaling factors |
| `errdef`, `iterate` | Lists of Pumplin settings forming the grid |
| `errdef_ref` | Reference setting for the plotted `ERRDEF` ratios |
| `n_iterations`, `enable_bartlett`, `q2_cut` | Steering-template options |
| `xfitter_tree`, `xfitter_commit`, `request_memory` | Worker build selection and Condor memory |

The runner adds a Gaussian λ = 0 group with no declared EoE sources, then
crosses every group with the `errdef` and `iterate` lists. Supply nonzero λ
values to avoid duplicating that automatic group. With *L*, *E* and *I* entries,
the requested count is `(L + 1) × E × I`. Every active source's strength is its
resolved ε multiplied by λ; `init` values are starting values, not fixed shifts.
The runner sets the Pumplin error block from the grid.

Template inputs comprise steering and parameter templates, constants and
weights. No reference-fit output is required. The CLI resolves `datafiles`
inside a fixed HERA dataset directory; another root cannot be selected in YAML
or by a CLI option. The library `run_scan` accepts `dataset_root`; see
[installation](../../../docs/installation.md) for the adapter/runtime boundary.

## Commands

Set `workspace` to **your existing scan directory** under `runs/scans/`.
The following commands are templates; the [HERA example](../../../docs/hera-scans.md#pumplin-stability)
provides a concrete configured grid. Run from the repository root after
installation.

Preview the grid without writing files:

```bash
python scripts/run-scan --dry-run "${workspace:?Set workspace to your scan directory}"
```

Generate inputs without submitting:

```bash
python scripts/run-scan --no-submit "${workspace:?Set workspace to your scan directory}"
```

Submit the generated batch:

```bash
bash "${workspace:?Set workspace to your scan directory}/runs/submit.sh"
```

After fitting, extract intervals and plot:

```bash
scripts/plot-scan "${workspace:?Set workspace to your scan directory}"
```

Generation writes the workspace's `runs/` tree. Use a separate workspace for a
changed grid; saved results need only the plotting command. Omitting both
generation flags generates and submits immediately.

## Outputs and implementation limits

Fits live at `runs/lambda_<value>/errdef<value>_iter<NN>/`. λ and `ERRDEF` are
formatted to one decimal and iteration to an integer; choose distinct names
when defining a grid. `runs/batch/fit_dirs.txt` records the job inventory and
`runs/batch/batch.log` records Condor events. Each fit's `output/minuit.out.txt`
supplies interval and covariance information.

| Output within the workspace | Contents |
| --- | --- |
| `results/pumplin_widths.csv` | Positive interval half-widths |
| `plots/pumplin_iteration_convergence.pdf` | Half-width relative to the largest available `ITERATE`, at fixed λ and `ERRDEF` |
| `plots/pumplin_errdef_invariance.pdf` | Half-width relative to reference `ERRDEF`, at fixed λ and `ITERATE` |
| `results/pumplin_eigenmode_contributions.csv` | Covariance contributions when suitable eigenmode records exist |
| `plots/pumplin_eigenmode_contributions/<parameter>.pdf` | Aligned contributions by parameter |
| `plots/pumplin_eigenmode_contributions_by_mode/mode_<NN>.pdf` | Aligned contributions by mode |

The current plotter selects a fixed list of standard HERAPDF PDF parameters
plus configured E-type nuisances. It does not discover arbitrary template
parameters automatically; another parametrisation may require a plotter
change. This is an implementation limit, not a restriction imposed by the grid
schema.

Compare the generated inventory with the available interval logs. Extraction
requires both `XRANGE: find allowed displacements` and
`ERROR MATRIX FROM ITERATE` markers; missing logs are absent from the reported
incomplete-block count. Completed blocks alone do not certify minimizer
convergence. Check fit status and raw outputs separately.

The plotter uses the largest available iteration and can substitute an
available `ERRDEF` when `errdef_ref` is absent. Verify these references and CSV
coverage before interpreting ratios near one as stability. The shaded 0.9–1.1
band is a visual guide, not an enforced acceptance test.
