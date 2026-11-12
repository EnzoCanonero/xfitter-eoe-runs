# Workspaces and workflow guides

[Repository](../README.md) · [Installation](../docs/installation.md) ·
[HERA and paper figures](../docs/hera-study.md)

Run commands from the repository root after installation. Each study has its
own workspace; use a new one when changing the scientific inputs.

## Choose a workflow

- [Fits](fits/README.md): prepare and submit an xFitter fit.
- [Forward selection](scans/forward-selection/README.md): rank candidate EoE sources.
- [EoE scans](scans/eoe-scan/README.md): vary source strengths.
- [Likelihood profiles](scans/likelihood/README.md): scan fixed parameter values.
- [Pumplin stability](scans/pumplin-stability/README.md): compare uncertainty settings.
- [PDF comparisons](comparisons/pdf/README.md): overlay PDFs and uncertainty bands.
- [Cross-section comparisons](comparisons/xsec/README.md): compare predictions with data.

## Workspace layout

- `runs/fits/<study>/`: inputs in `config/`, launcher in `condor/`, results in `output/`.
- `runs/scans/<family>/<study>/`: `config.yaml`, generated fits in `runs/`,
  extracted data in `results/`, figures in `plots/`.
- `runs/comparisons/<family>/<study>/`: `config.yaml` and generated `plots/`.

Further nesting is allowed. Git stores study definitions, not generated outputs.
Scans generate their own fits; comparisons need completed outputs or PDF sets.

## Shared scan configuration

Create a `config.yaml` with these inputs, then add the fields in the chosen
scan guide. Replace the example template and data paths for your study.

```yaml
template: hera-baseline
dataset_root: /path/to/datasets
datafiles: [sample.dat]
```

- `template` selects a directory in `templates/` with steering and parameter
  templates, constants and weights.
- `dataset_root` is absolute or relative to `config.yaml`; `datafiles` lists
  the files to copy from it.
- Source names must match the data. Source `init` sets a starting value;
  `epsilon` can override the source strength individually.
- Optional settings include `q2_cut`, `n_iterations` for nuisance profiling,
  and `enable_bartlett`. Ranking and EoE scans also accept `doErrors`.
- `xfitter_tree`, `xfitter_commit` and `request_memory` select the worker build,
  optional revision and Condor memory. See [environment setup](../docs/installation.md#environment-setup)
  and [using your own build](fits/README.md#use-your-own-xfitter-build).

The scan guides show preview, generation, submission and plotting separately.
`--dry-run` writes nothing; `--no-submit` generates files only. Running
`python scripts/run-scan WORKSPACE` without either flag generates and submits.
To replot completed results, run only `scripts/plot-scan WORKSPACE`.
