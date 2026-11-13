# Workspaces and workflow guides

[Repository](../README.md) · [Installation](../docs/installation.md) ·
[HERA and paper figures](../docs/hera-study.md)

Each study has its own workspace; use a new one when changing the scientific
inputs. Commands run from the repository root.

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
