# xFitter EoE Runs

[![Tests](https://github.com/EnzoCanonero/xfitter-eoe-runs/actions/workflows/tests.yml/badge.svg?branch=master)](https://github.com/EnzoCanonero/xfitter-eoe-runs/actions/workflows/tests.yml)

Workspace for the xFitter errors-on-errors studies. The repository keeps
reusable code, commands, templates, datasets, and execution workspaces in
separate top-level directories. Each scan or comparison configuration lives
with its generated products under `runs/`; generated results and local
historical artifacts are not tracked by Git.

## Layout

```text
xfitter-eoe-runs/
├── src/                         # installable Python package
│   └── xfitter_eoe_runs/
│       ├── cli/                 # repository-aware command adapters
│       ├── comparisons/
│       └── scans/
├── scripts/                     # user-facing commands and environment setup
├── templates/                   # named xFitter scan templates
├── runs/                        # tracked configurations and local artifacts
│   ├── README.md                # catalog of paper and auxiliary studies
│   ├── fits/<setup>/<fit>/       # manual fit configs, launchers, and outputs
│   ├── scans/<type>/<setup>/    # study configs and generated scan products
│   └── comparisons/<type>/<setup>/ # study configs, tables, and plots
├── datasets/                    # canonical input data
├── tests/
├── legacy-artifacts.yaml        # provenance for local historical material
└── legacy/                      # ignored local archive; absent in fresh clones
```

Generated directories under `runs/` may be absent in a fresh clone; commands
create them when needed. The enclosing workspaces and their `config.yaml` files
are tracked. The [run catalog](runs/README.md) lists the 13 fit workspaces,
30 scan configurations, and 11 comparisons retained in the current tree.

## Boundaries

- `src/xfitter_eoe_runs/scans/` and `comparisons/` contain the path-agnostic
  reusable implementation.
- `src/xfitter_eoe_runs/cli/` contains the repository-aware plotting command
  adapters. `scripts/` keeps all public commands and environment setup; the
  plotting wrappers prepare external runtimes and invoke those adapters.
- `templates/` contains reusable scan inputs only. Generated fits, plots, tables,
  logs, and results do not belong there.
- `datasets/` is input-only. Commands may copy data into a run workspace but do
  not write results back into the dataset tree.
- `runs/` owns execution workspaces. Each scan and comparison workspace keeps
  its tracked `config.yaml` beside its ignored runtime products. Comparison
  configurations and likelihood references may consume fit workspaces under
  `runs/fits/`; reusable code never lives under `runs/`.

The flow remains one way: entry points and CLI adapters call reusable code,
inputs feed executions, and executions write only to their workspace under
`runs/`.

## Requirements

- Linux with Bash and Python 3.9 or newer.
- [xFitter](https://gitlab.cern.ch/fitters/xfitter/-/wikis/Installation-script),
  installed separately in a location visible to worker nodes.
- HTCondor, with `condor_submit` on `PATH` and access to a configured pool, for
  submitted runs.

`pip` installs this package and its Python dependencies. It does not install
xFitter, HTCondor, LHAPDF, ROOT, or custom xFitter build trees. Generated
xFitter workers and environment-bootstrap wrappers assume the CERN LCG views
under `/cvmfs/sft.cern.ch` and a shared filesystem. Condor jobs do not transfer
files, so the checkout, run workspaces, and xFitter installation must all be
visible to worker nodes.

## Setup

1. Clone the repository to the shared filesystem and enter its root.
2. Install the package and its Python dependencies:

   ```bash
   python3 -m pip install .
   ```

   For development, use an editable installation instead:

   ```bash
   python3 -m pip install -e .
   ```

3. Set the installation paths and default build in `.env`. `XFITTER_ROOT`
   contains the worktrees; `XFITTER_SETUP_ROOT` contains `setup.sh` and shared
   dependencies. Both locations must be visible to Condor worker nodes. If
   `XFITTER_SETUP_ROOT` is omitted, it defaults to `XFITTER_ROOT`.

   ```bash
   XFITTER_ROOT=/nfs/scratch2/ecanoner/PDF
   XFITTER_SETUP_ROOT=/nfs/scratch2/ecanoner/PDF/merge-master
   XFITTER_TREE=merge-master/xfitter-master
   XFITTER_COMMIT=67398b15571dff1e9ddce0bc88923554552c9c84
   ```

4. For interactive xFitter use, source the environment:

   ```bash
   source scripts/setup-env.sh
   ```

   When switching an already configured shell to the repository default, first
   run `unset XFITTER_TREE XFITTER_COMMIT`; otherwise those existing values
   intentionally override `.env`.

Commands resolve the repository root from their own location, so run them from
the repository root without creating per-workspace symlinks.

Scan configurations may set `xfitter_tree` to select a build directory below
`$XFITTER_ROOT`, and may pair it with `xfitter_commit`, a full 40-character Git
SHA-1. Generated workers export both values; `scripts/setup-env.sh` stops before
running xFitter if the selected tree's `HEAD` does not match the requested
commit or if tracked files differ from that commit. Untracked build products do
not invalidate the pin. Values exported by the caller or generated worker take
precedence over repository `.env` defaults. Selecting a tree explicitly
without a commit also suppresses any default-tree commit pin from `.env`, so
retained jobs are not checked against an unrelated revision. For example:

```yaml
xfitter_tree: merge-master/xfitter-master
xfitter_commit: 67398b15571dff1e9ddce0bc88923554552c9c84
```

The value above pins the build installed from `mr/errors-on-errors-20260903`
on 2026-09-29. Update the pin after checking out and rebuilding another revision.
A branch name is not a commit pin, and `XFITTER_TREE` names a directory relative
to `XFITTER_ROOT` (or an absolute path), rather than a Git branch.

Changing `.env` does not migrate existing studies: their configurations and
generated launchers retain their own tree and commit selections. For a new run
on the current build, create a separate workspace with the desired tree and
commit and generate its launchers. Retained configurations using the old
`xfitter-master` path and `bd0470d...` pin need a build of that revision to be
reproduced; the relocated current build has a different commit. Preserve those
historical configurations and results when creating a new study.

The FONLL-C and resummed fits require the APFEL 3.0.6/HELL 3 dependencies.
All 13 current paper fit launchers select `merge-master/xfitter-master` at
`67398b15571dff1e9ddce0bc88923554552c9c84`, including the small-x fits. Auxiliary
and archived studies retain their own build selections, which may use the older
`xfitter-bartlett-apfel306-hell3` tree. Launchers and descriptors contain
site-specific absolute paths that must be adapted for a different checkout or
installation; see the [fit catalog](runs/README.md#fits).

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
runs/fits/<setup>/<fit>/
├── config/                      # xFitter inputs
├── condor/submit.sh             # tracked launcher
└── output/                      # generated and ignored
```

Create a fit from the current HERAPDF2.0 Gaussian configuration (the default):

```bash
scripts/new-fit herapdf20-nnlo-rtopt/my-study/variant-a
```

Or use another fit configuration as the template:

```bash
scripts/new-fit \
  herapdf20-nnlo-rtopt/my-study/variant-b \
  herapdf20-nnlo-rtopt/eoe-selected/config
```

`scripts/new-fit` copies the configuration and required files from `datasets/`.
The generated `submit.sh` creates the ignored Condor files, sets the absolute
output path, and submits the job:

```bash
runs/fits/herapdf20-nnlo-rtopt/my-study/variant-a/condor/submit.sh
```

Small-x workspaces use the `herapdf-bg-nnlo-fonll-c` and
`herapdf-bg-nnlo-nllx-fonll-c` setup directories. Their existing launchers remain
with the fit workspace; the fixed-order Gaussian fit is the matched reference
used in the paper, not an auxiliary study.

## Scan workspaces

Each scan workspace contains its tracked definition and local generated
products:

```text
runs/scans/<type>/<setup>/<study>/
├── config.yaml                  # tracked definition
├── runs/                        # generated xFitter jobs
├── results/                     # generated extracted results
└── plots/                       # generated figures
```

Each `config.yaml` selects a named template from root `templates/`. Pass the
workspace directory directly to the commands:

```bash
workspace=runs/scans/eoe-scan/herapdf20-nnlo-rtopt/common-epsilon

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
plots or tables under `runs/comparisons/<type>/<setup>/<study>/`.

The supported definition types and commands are:

- `pdf-comparison` — `scripts/plot-pdf-comparison <workspace-dir>`
- `xsec-comparison` — `scripts/plot-xsec <workspace-dir>`
- `xsec-region-table` — `scripts/plot-xsec <workspace-dir>`

PDF comparisons require the LHAPDF Python bindings (`import lhapdf`).
Cross-section plots require `xfitter-draw` and ROOT. These external components
are expected from the configured xFitter/LCG environment and are not installed
by this Python package. Fresh comparisons default to `merge-master/xfitter-master`; set
`xfitter_tree` in the comparison configuration or export `XFITTER_TREE` to use
another compatible built tree. Retained historical and small-x studies should
continue to select the build with which they were produced.

For the current paper workspaces:

```bash
scripts/plot-pdf-comparison \
  runs/comparisons/pdf/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected

scripts/plot-xsec \
  runs/comparisons/xsec/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected-low-q2

scripts/plot-scan \
  runs/scans/eoe-scan/herapdf20-nnlo-rtopt/common-epsilon
```

Local fit paths in a comparison config are resolved relative to its workspace.
A typical entry therefore looks like:

```yaml
fits:
  - label: Gaussian
    setup: HERAPDF2.0, NNLO, RTOPT
    treatment: Gaussian
    path: ../../../../fits/herapdf20-nnlo-rtopt/gaussian
    source: xfitter-grid
  - label: EoE
    setup: HERAPDF2.0, NNLO, RTOPT
    treatment: EoE
    path: ../../../../fits/herapdf20-nnlo-rtopt/eoe-selected
    source: xfitter-grid
```

Local comparisons require a populated `<fit>/output/`. Historical directories
such as `output_legacy_*` or `output_retained_*` are not promoted automatically.
PDF comparisons write combined, ratio-only, and absolute-only PDFs beneath the
workspace's `plots/` directory.

### Current paper plots and individual panels

The source code and the following configurations define the final paper
presentation. The native PDFs in each workspace's `plots/` directory use the
same labels and typography as the assembled paper figures.

| Figure | Workspace configuration | Presentation |
| --- | --- | --- |
| 1 | [Common epsilon scan](runs/scans/eoe-scan/herapdf20-nnlo-rtopt/common-epsilon/config.yaml) | Original titleless format; axis labels 20 pt, ticks 15 pt |
| 2 | [HERAPDF2.0 comparison](runs/comparisons/pdf/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected/config.yaml) | HERAPDF2.0, NNLO, RTOPT; Gaussian/EoE |
| 3 | [Cross sections](runs/comparisons/xsec/herapdf20-nnlo-rtopt/gaussian-vs-eoe-selected-low-q2/config.yaml) | Gaussian/EoE; no setup heading; Q² labels include GeV²; original text sizes |
| 4 | [HERAPDF-BG comparison](runs/comparisons/pdf/herapdf-bg-nnlo-rtopt/gaussian-vs-eoe-selected/config.yaml) | HERAPDF-BG, NNLO, RTOPT; Gaussian/EoE |
| 5 | [Resummed comparison](runs/comparisons/pdf/herapdf-bg-nnlo-nllx-fonll-c/gaussian-vs-eoe-selected/config.yaml) | HERAPDF-BG, NNLO+NLLₓ, FONLL-C; Gaussian/EoE |
| 6 | [Three informed setups](runs/comparisons/pdf/cross-setups/eoe-informed/config.yaml) | No heading; HERAPDF2.0 / HERAPDF-BG / HERAPDF-BG NNLO+NLL; 13 pt legend; Ratio to HERAPDF2.0 |
| 7 | [2 iterations](runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter02/config.yaml), [4 iterations](runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter04/config.yaml), [8 iterations](runs/comparisons/pdf/herapdf20-nnlo-rtopt/numerical-vs-iter08/config.yaml) | HERAPDF2.0, NNLO, RTOPT; Numerical/Iterative; Ratio to Numerical |

Every PDF-comparison workspace writes three files with the same observable page
order from its `observables` configuration:

- `plots/pdf_comparison.pdf`: absolute and ratio panels side by side.
- `plots/pdf_comparison_absolute.pdf`: individual absolute panels.
- `plots/pdf_comparison_ratio.pdf`: individual ratio panels.

PDF-comparison panel titles and axis labels are 22 pt, ticks 18 pt, and legends
15 pt. Setup headings remain 16 pt. Figure 6 overrides only its legend size to
13 pt, including the Q² entry, in all three output variants. The Gaussian/EoE
comparisons label ratios as `Ratio to Gaussian`.

Fit entries keep the full physical `setup` separate from the displayed
`treatment`. Use `NLL_x` in setup metadata to render a subscript. The optional
`presentation` mapping controls `title` (`null` hides the shared heading),
`use_fit_labels`, `ratio_reference_label`, and `legend_fontsize`. Figure 6 uses:

```yaml
presentation:
  title: null
  use_fit_labels: true
  ratio_reference_label: HERAPDF2.0
  legend_fontsize: 13
```

The cross-section configuration sets `show_setup_annotation: false`. The common
epsilon scan selects `plot_style: paper-common-epsilon` and
`plot_font_size_offset: 2`; generic lambda scans retain their own coordinates
and layout.

Assemble paper layouts separately from the repository. The native files retain
their filenames, dimensions and page order; generated plots remain ignored by
Git. Superseded workspaces are retained under `legacy/cleanup-20261111/`.
The canonical configurations above retain the paper campaign's original inputs.
Auxiliary studies keep their own input identities, including references to
archived fits; renaming a study does not substitute newer fitted results.

## Datasets and historical material

Canonical xFitter tables live under `datasets/`; see `datasets/README` for the
upstream data repository. Runtime copies belong under `runs/` and are ignored.

Inactive fits, studies, and other historical material are retained locally
under the ignored `legacy/` tree. `legacy-artifacts.yaml` records their original
locations and provenance, including the 2026-11-11 run-tree cleanup. Historical
manifest sections intentionally retain the paths that were current when each
snapshot was classified. The ignored archive is local material, so an auxiliary
study referring to it requires those inputs to be available on the checkout.

## Validation

After installing the package, run:

```bash
python3 -m unittest discover -s tests -v
```

## Git workflow

- Use a branch per change or study.
- Keep study rationale in its workspace `config.yaml` comments or a local
  `README.md`.
- Commit configurations, templates, source, commands, tests, and documentation.
- Do not commit outputs, Condor logs, copied data tables, or `legacy/` payloads.
