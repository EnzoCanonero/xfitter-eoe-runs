# Profile-likelihood scans

[Repository](../../../README.md) · [Installation](../../../docs/installation.md) ·
[HERA study](../../../docs/hera-study.md) ·
[HERA examples](../../../docs/hera-scans.md#likelihood-profiles) ·
[Paper reproduction](../../../docs/reproducing-paper.md)

`scan_type: likelihood-scan` fixes one parameter, or a pair of parameters, on a
grid and reoptimizes the remaining free parameters. The reference fit supplies
starting values, errors and nuisance-parameter identities. The resulting
profiles describe departures from a quadratic approximation.

## Configuration and reference inputs

Create a `config.yaml` in a workspace under `runs/scans/`.

| Field | Meaning |
| --- | --- |
| `scan_type` | `likelihood-scan` |
| `template`, `datafiles` | Named root template and dataset filenames for generated fits |
| `dataset_root` | Dataset directory, relative to the directory containing `config.yaml`; absolute and `~` paths also work |
| `reference_fit` | Reference fit root, resolved relative to the scan workspace |
| `systematics`, `epsilon` | Source declarations and default EoE strength; entries can supply their own strength and initial value |
| `scan_defaults` | 1D defaults `n_sigma`, `npoints`; 2D defaults `n_sigma_2d`, `npoints_2d` |
| `scan_params_1d` | PDF parameter entries with `name`; optional `n_sigma`, `npoints`, or explicit `min` and `max` |
| `scan_systematics_1d` | Same grid fields for declared E-type nuisance parameters |
| `scan_params_2d` | Entries with `pair: [xName, yName]`; optional `n_sigma`, `npoints`, `x_range`, `y_range` |
| `parameter_overrides` | Optional PDF starting-value/step overrides by parameter name |
| `n_iterations`, `enable_bartlett`, `q2_cut`, `doErrors` | Steering and error-calculation options |
| `xfitter_tree`, `xfitter_commit`, `request_memory` | Worker build selection and Condor memory |

At least one scan list is required. By default, each axis spans the reference
value ± `n_sigma` times its reference error. A 2D entry generates an
`npoints × npoints` grid, fixing both axes while profiling other parameters.
When `n_sigma_2d` is omitted, the 2D range is derived from the optional
`sigma_levels` list (default `[1, 2, 3]`).

Even a dry run reads `reference_fit/output/minuit.out.txt`. Retain the reference
`config/steering.txt` for the authoritative E-source order: MINUIT truncates
names, so the generator uses parameter indices and that declaration order to
identify nuisances. The configured E-source set must agree with the reference.
Changing the reference changes the study and its grid.

The template supplies steering, parameters, constants and weights.
`scripts/run-scan` copies `datafiles` from the configured `dataset_root`.
The library `run_scan` uses that root when its `dataset_root` argument is
`None`; an explicit path overrides it. See
[installation](../../../docs/installation.md#datasets-and-custom-studies) for
a path example. Parameter updates expect inline `[value, step]` entries,
with a special case for the bundled `CDbar` mapping; arbitrary mapping-style
parameter definitions may need an adapter change.

## Commands

Set `workspace` to **your existing scan directory** under `runs/scans/`, with
its reference outputs available. These are command templates; concrete
configurations are in the [HERA examples](../../../docs/hera-scans.md#likelihood-profiles).
Run from the repository root after installation.

Preview reference parameters, ranges and fit counts:

```bash
python scripts/run-scan --dry-run "${workspace:?Set workspace to your scan directory}"
```

Generate inputs and the manifest without submitting:

```bash
python scripts/run-scan --no-submit "${workspace:?Set workspace to your scan directory}"
```

Submit the generated batch:

```bash
bash "${workspace:?Set workspace to your scan directory}/runs/submit.sh"
```

After fitting, extract profiles and plot:

```bash
scripts/plot-scan "${workspace:?Set workspace to your scan directory}"
```

Generation writes the workspace's `runs/` tree. Use a separate workspace for a
changed reference/grid. Existing results need only the plotting command;
omitting both generation flags generates and submits immediately.

## Outputs and interpretation

| Output within the workspace | Contents |
| --- | --- |
| `runs/scan_manifest.json` | Reference information, grid coordinates and fit names |
| `runs/1d_<parameter>_<index>/`, `runs/2d_<x>_<y>_<i>_<j>/` | Individual fixed-parameter fits |
| `runs/batch/fit_dirs.txt`, `runs/batch/batch.log` | Generated inventory and submitted Condor events |
| `results/profiles_1d.csv`, `plots/profiles_1d.pdf` | 1D profiles and convergence flags, when requested |
| `results/grids_2d.csv` | 2D point statistics and status, when requested |
| `plots/likelihood_2d_convergence.pdf`, `plots/likelihood_2d_profiles.pdf` | 2D convergence and profile-slice diagnostics |
| `results/quadratic_fit_summary.txt` | 2D quadratic diagnostic summary |

The 1D Δχ² uses raw minimized χ², not the Bartlett-corrected goodness-of-fit
statistic used in source rankings. It is normalized to the scan point closest
to the reference value; if that point has no finite χ², extraction falls back
to the lowest available finite value. The plot does not apply an additional
confidence-interval Bartlett correction.

Check the manifest against every requested parameter and grid size: missing
reference parameters can be skipped during generation. Inspect missing χ² and
`converged` flags in the CSVs; 1D plots omit points marked non-converged. Review
the central point and questionable fits in raw `Results.txt` and
`minuit.out.txt` before drawing conclusions. A smooth curve with omitted points
does not establish grid completeness or validate interval coverage.
