# xFitter EoE Runs

Workspace for the xFitter errors-on-errors studies. The repository keeps study
definitions, reusable code, commands, datasets, and execution workspaces in
separate top-level directories. Generated results and local historical
artifacts are not tracked by Git.

## Layout

```text
xfitter-eoe-runs/
├── src/                         # reusable Python implementation
│   └── xfitter_eoe_runs/
│       ├── scans/
│       └── comparisons/
├── scripts/                     # user-facing commands and environment setup
├── studies/                     # declarative study inputs
│   ├── scans/                   # scan config.yaml files
│   ├── comparisons/             # comparison config.yaml files
│   └── templates/               # named xFitter scan templates
├── runs/                        # execution workspaces and generated artifacts
│   ├── fits/                    # manual fit configs, launchers, and outputs
│   ├── scans/                   # generated scan fits, results, and plots
│   └── comparisons/             # generated comparison results and plots
├── datasets/                    # canonical input data
├── tests/
├── legacy-artifacts.yaml        # provenance for local historical material
└── legacy/                      # ignored local archive; absent in fresh clones
```

Empty or generated directories under `runs/` may be absent in a fresh clone;
the commands create them when needed.

## Boundaries

- `src/` contains path-agnostic implementation code. It does not import from or
  discover `scripts/`, `studies/`, `runs/`, or `datasets/`.
- `scripts/` contains the entry points. Commands import `src/`, read definitions
  from `studies/` and inputs from `datasets/`, and write runtime data to `runs/`.
- `studies/` contains configuration and templates only. Generated fits, plots,
  tables, logs, and results do not belong there.
- `datasets/` is input-only. Commands may copy data into a run workspace but do
  not write results back into the dataset tree.
- `runs/` contains execution workspaces. Comparison definitions may reference
  fit workspaces under `runs/fits/`, as may likelihood reference definitions.
  Definitions do not consume generated `runs/scans/` or `runs/comparisons/`
  products, and reusable code never lives under `runs/`.

The resulting flow is one way: commands call reusable code, definitions and
datasets feed executions, and executions write to `runs/`.

## Setup

1. Clone the repository to an NFS-accessible location.
2. Set `XFITTER_ROOT` in `.env` to the xFitter installation visible to Condor
   worker nodes.
3. For interactive xFitter use, source the environment:

```bash
source scripts/setup-env.sh
```

Commands resolve the repository root from their own location, so run them from
the repository root without creating per-study symlinks.

## Commands

| Command | Purpose |
| --- | --- |
| `scripts/new-fit` | Create a manual workspace under `runs/fits/` |
| `scripts/run-scan` | Preview, generate, or submit a scan study |
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

## Scan studies

Scan definitions live under `studies/scans/`. Each `config.yaml` selects a
named template from `studies/templates/`. The same relative path is used for
the runtime workspace:

```text
studies/scans/<study>/config.yaml
                         │
                         └──> runs/scans/<study>/
                              ├── runs/
                              ├── results/
                              └── plots/
```

Use an existing definition as the starting point for a new study, then pass its
directory explicitly to the commands:

```bash
study=studies/scans/lambda/hera-baseline/greedy-selection

scripts/run-scan --dry-run "$study"   # preview only
scripts/run-scan "$study"             # generate and submit
scripts/plot-scan "$study"            # extract results and plot
```

Use `scripts/run-scan --no-submit "$study"` instead of the submission command
when the run directories should be generated without submitting Condor jobs.

The existing scan types are:

- `lambda-scan`: scan epsilon scaling factors.
- `systematic-ranking`: test systematic sources individually.
- `likelihood-scan`: profile one- or two-dimensional chi-squared grids around a
  reference fit.
- `pumplin-stability`: scan lambda, `ERRDEF`, and `ITERATE` settings.

Likelihood generation requires the configured reference fit's
`config/steering.txt` and `output/minuit.out.txt`. Outputs are ignored, so the
reference output must exist locally before running the study.

## Comparison studies

Comparison definitions live under `studies/comparisons/`; their generated
plots and tables use the matching path under `runs/comparisons/`.

The supported definition types and commands are:

- `pdf-comparison` — `scripts/plot-pdf-comparison <study-dir>`
- `xsec-comparison` — `scripts/plot-xsec <study-dir>`
- `xsec-region-table` — `scripts/plot-xsec <study-dir>`

For example:

```bash
scripts/plot-pdf-comparison \
  studies/comparisons/baseline-nominal-vs-7sources

scripts/plot-xsec \
  studies/comparisons/xsec-nc-cc-nominal-vs-7sources-pumplin
```

Local fit paths in a comparison config are resolved relative to its study
directory. A typical entry therefore looks like:

```yaml
fits:
  - label: HERA baseline
    path: ../../../runs/fits/hera-baseline/nominal-bartlett2-pumplin
```

Local comparisons require a populated `<fit>/output/`. Historical directories
such as `output_legacy_*` or `output_retained_*` are not promoted automatically.
PDF comparisons write combined, ratio-only, and absolute-only PDFs beneath the
matching `runs/comparisons/<study>/plots/` directory.

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
- Keep study rationale in its `config.yaml` comments or a local `README.md`.
- Commit definitions, source, commands, tests, and documentation.
- Do not commit outputs, Condor logs, copied data tables, or `legacy/` payloads.
