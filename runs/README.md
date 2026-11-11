# Workspaces and workflow guides

[Project overview](../README.md) · [Installation](../docs/installation.md) ·
[HERA application and catalog](../docs/hera-study.md)

`runs/` contains study definitions alongside their generated results. A workspace
identifies one fit, scan or comparison. The scientific configuration determines
the inputs and calculation; directory names organize the work.

## Choose a workflow

| Task | Definition | Guide |
| --- | --- | --- |
| Standalone fit | xFitter files in `config/`, launcher in `condor/` | [Fit workspaces](fits/README.md) |
| Rank candidate EoE sources | `scan_type: systematic-ranking` | [Forward selection](scans/forward-selection/README.md) |
| Scale errors on errors | `scan_type: lambda-scan` | [EoE scans](scans/eoe-scan/README.md) |
| Profile fitted parameters | `scan_type: likelihood-scan` | [Likelihood profiles](scans/likelihood/README.md) |
| Vary error-calculation settings | `scan_type: pumplin-stability` | [Pumplin stability](scans/pumplin-stability/README.md) |
| Compare parton distributions | `type: pdf-comparison` | [PDF comparisons](comparisons/pdf/README.md) |
| Overlay selected DIS cross sections | `type: xsec-comparison` | [Cross-section comparisons](comparisons/xsec/README.md) |
| Compare data χ² in Q²–x bins | `type: xsec-region-table` | [Regional tables](comparisons/regions/README.md) |

The scan commands require a workspace under `runs/scans/`; comparison commands
require one under `runs/comparisons/`. Further nesting is allowed. For example:

```text
runs/
├── fits/<study>/
│   ├── config/
│   ├── condor/submit.sh
│   └── output/                     # generated
├── scans/<family>/<study>/
│   ├── config.yaml
│   ├── runs/                       # generated fit jobs and batch files
│   ├── results/                    # extracted numerical results
│   └── plots/                      # generated figures
└── comparisons/<family>/<study>/
    ├── config.yaml
    ├── results/                    # generated tables, where applicable
    └── plots/                      # generated figures, where applicable
```

## Inputs and execution

Fit configurations specify the physics calculation and data inputs. Scan
configurations select a template from `templates/`, source settings and scan
coordinates. Each scan's `dataset_root` selects its input directory, resolved
relative to `config.yaml` unless absolute; `~` paths are supported. Its
`datafiles` list names the files to copy from that directory.
Comparison configurations select existing fitted outputs or PDF
sets and the quantities to display. Comparison fit paths are relative to their
workspace; outputs are written beneath that same workspace.

Preview a configured scan with `python scripts/run-scan --dry-run WORKSPACE`.
Use `--no-submit` to generate files without sending jobs. Omitting both flags
generates and submits; a fit's `condor/submit.sh` also submits immediately.
The guides explain the prerequisites and products for each command.

For changed scientific inputs, use a separate workspace to preserve previous
results. Replotting completed results only requires the relevant plotting
command. Generation and plotting can replace existing files at their configured
destinations.

## Supplied application

The [HERA catalog](../docs/hera-study.md) links all bundled configurations and
defines their setup and treatment notation. Its fit settings, comparison scales
and kinematic selections are examples of the workflows above. Consult the
individual guides for input-format requirements and current implementation
limits when preparing another application.

Commit study definitions and launchers. Generated fit outputs, scan jobs,
extracted results, figures and runtime logs are excluded from Git.
