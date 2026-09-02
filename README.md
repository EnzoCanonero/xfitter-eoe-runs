# xFitter EoE Runs

Workspace for the xFitter errors-on-errors studies. The repository keeps
reusable code, commands, templates, datasets, and execution workspaces in
separate top-level directories. Each scan or comparison configuration lives
with its generated products under `runs/`; generated results and local
historical artifacts are not tracked by Git.

## Layout

```text
xfitter-eoe-runs/
├── src/                         # reusable Python implementation
│   └── xfitter_eoe_runs/
│       ├── scans/
│       └── comparisons/
├── scripts/                     # user-facing commands and environment setup
├── templates/                   # named xFitter scan templates
├── runs/                        # tracked configurations and local artifacts
│   ├── fits/                    # manual fit configs, launchers, and outputs
│   ├── scans/<study>/           # config.yaml, generated fits, results, plots
│   └── comparisons/<study>/     # config.yaml, generated results and plots
├── datasets/                    # canonical input data
├── tests/
├── legacy-artifacts.yaml        # provenance for local historical material
└── legacy/                      # ignored local archive; absent in fresh clones
```

Generated directories under `runs/` may be absent in a fresh clone; commands
create them when needed. The enclosing workspaces and their `config.yaml` files
are tracked.

## Boundaries

- `src/` contains path-agnostic implementation code. It does not import from or
  discover `scripts/`, `templates/`, `runs/`, or `datasets/`.
- `scripts/` contains the entry points. Commands import `src/`, read the selected
  workspace configuration, templates, and datasets, then write generated data
  back into that workspace.
- `templates/` contains reusable scan inputs only. Generated fits, plots, tables,
  logs, and results do not belong there.
- `datasets/` is input-only. Commands may copy data into a run workspace but do
  not write results back into the dataset tree.
- `runs/` owns execution workspaces. Each scan and comparison workspace keeps
  its tracked `config.yaml` beside its ignored runtime products. Comparison
  configurations and likelihood references may consume fit workspaces under
  `runs/fits/`; reusable code never lives under `runs/`.

The flow remains one way: commands call reusable code; workspace configurations,
templates, and datasets feed executions; executions write only to their
workspace under `runs/`.

## Setup

1. Clone the repository to an NFS-accessible location.
2. Set `XFITTER_ROOT` in `.env` to the xFitter installation visible to Condor
   worker nodes.
3. For interactive xFitter use, source the environment:

```bash
source scripts/setup-env.sh
```

Commands resolve the repository root from their own location, so run them from
the repository root without creating per-workspace symlinks.

## Commands

| Command | Purpose |
| --- | --- |
| `scripts/new-fit` | Create a manual workspace under `runs/fits/` |
| `scripts/run-scan` | Preview, generate, or submit a scan workspace |
| `scripts/plot-scan` | Extract completed scan results and create plots |
| `scripts/plot-pdf-comparison` | Plot a configured PDF comparison |
| `scripts/plot-xsec` | Plot a cross-section comparison or create a region table |
| `scripts/fix-lhapdf-info` | Repair metadata for an existing xFitter LHAPDF output |

## Manual fits

Fits created by `scripts/new-fit` and the retained HERA workspaces have this
shape:

```text
runs/fits/<group>/<fit>/
├── config/                      # xFitter inputs
├── condor/submit.sh             # tracked launcher
└── output/                      # generated and ignored
```

Create a fit from the retained HERA baseline configuration:

```bash
scripts/new-fit hera-baseline/my-study/variant-a
```

Or use another fit configuration as the template:

```bash
scripts/new-fit \
  hera-baseline/my-study/variant-b \
  hera-baseline/baseline-7-sources-bartlett2-pumplin/config
```

`scripts/new-fit` copies the configuration and required files from `datasets/`.
The generated `submit.sh` creates the ignored Condor files, sets the absolute
output path, and submits the job:

```bash
runs/fits/hera-baseline/my-study/variant-a/condor/submit.sh
```

The retained small-x studies keep their existing grouped batch launchers under
`runs/fits/smallx-resummation/`.

## Scan workspaces

Each scan workspace contains its tracked definition and local generated
products:

```text
runs/scans/<study>/
├── config.yaml                  # tracked definition
├── runs/                        # generated xFitter jobs
├── results/                     # generated extracted results
└── plots/                       # generated figures
```

Each `config.yaml` selects a named template from root `templates/`. Pass the
workspace directory directly to the commands:

```bash
workspace=runs/scans/lambda/hera-baseline/greedy-selection

scripts/run-scan --dry-run "$workspace"   # preview only
scripts/run-scan "$workspace"             # generate and submit
scripts/plot-scan "$workspace"            # extract results and plot
```

Use `scripts/run-scan --no-submit "$workspace"` instead of the submission
command when the run directories should be generated without submitting Condor
jobs.

The existing scan types are:

- `lambda-scan`: scan epsilon scaling factors.
- `systematic-ranking`: test systematic sources individually.
- `likelihood-scan`: profile one- or two-dimensional chi-squared grids around a
  reference fit.
- `pumplin-stability`: scan lambda, `ERRDEF`, and `ITERATE` settings.

Likelihood generation requires the configured reference fit's
`config/steering.txt` and `output/minuit.out.txt`. Outputs are ignored, so the
reference output must exist locally before running the workspace.

## Comparison workspaces

Each comparison workspace keeps its tracked `config.yaml` beside its ignored
plots or tables under `runs/comparisons/<study>/`.

The supported definition types and commands are:

- `pdf-comparison` — `scripts/plot-pdf-comparison <workspace-dir>`
- `xsec-comparison` — `scripts/plot-xsec <workspace-dir>`
- `xsec-region-table` — `scripts/plot-xsec <workspace-dir>`

For example:

```bash
scripts/plot-pdf-comparison \
  runs/comparisons/baseline-nominal-vs-7sources

scripts/plot-xsec \
  runs/comparisons/xsec-nc-cc-nominal-vs-7sources-pumplin
```

Local fit paths in a comparison config are resolved relative to its workspace.
A typical entry therefore looks like:

```yaml
fits:
  - label: HERA baseline
    path: ../../fits/hera-baseline/nominal-bartlett2-pumplin
```

Local comparisons require a populated `<fit>/output/`. Historical directories
such as `output_legacy_*` or `output_retained_*` are not promoted automatically.
PDF comparisons write combined, ratio-only, and absolute-only PDFs beneath the
workspace's `plots/` directory.

## Datasets and historical material

Canonical xFitter tables live under `datasets/`; see `datasets/README` for the
upstream data repository. Runtime copies belong under `runs/` and are ignored.

Inactive fits, studies, and other historical material are retained locally
under the ignored `legacy/` tree. `legacy-artifacts.yaml` records their original
locations and provenance. Historical manifest sections intentionally retain
the paths that were current when each snapshot was classified.

## Validation

Run the repository tests directly from the source tree:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Git workflow

- Use a branch per change or study.
- Keep study rationale in its workspace `config.yaml` comments or a local
  `README.md`.
- Commit configurations, templates, source, commands, tests, and documentation.
- Do not commit outputs, Condor logs, copied data tables, or `legacy/` payloads.
