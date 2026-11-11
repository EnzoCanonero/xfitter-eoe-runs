# Installation and environment

[Project overview](../README.md) · [Study catalog](../runs/README.md) ·
[Fit workspaces](../runs/fits/README.md) · [HERA study](hera-study.md)

Prepare the Python environment to inspect configurations and preview jobs.
Prepare the scientific runtime before executing fits or plotting results that
need compiled libraries. Commands below run in Bash from the repository root
unless stated otherwise.

## Get the documented checkout

The commands and layout documented here are on
`compat/errors-on-errors-20260903`:

```bash
git clone --branch compat/errors-on-errors-20260903 \
  https://github.com/EnzoCanonero/xfitter-eoe-runs.git
cd xfitter-eoe-runs
```

For batch execution, place the checkout on a filesystem visible at the same
path on the submission host and worker nodes. A clone includes tracked study
inputs and tools, but no fit outputs, extracted results or plots.

## Python installation

Use Python 3.9 or newer. A virtual environment beside the checkout keeps local
dependencies out of the repository:

```bash
python3 -m venv ../xfitter-eoe-venv
source ../xfitter-eoe-venv/bin/activate
python -m pip install .
```

The package installs Jinja2, matplotlib, NumPy, pandas and PyYAML. For
development, replace the final command with `python -m pip install -e .`.

Check the installed modules and inspect the scan command without creating or
submitting a study:

```bash
python -c "import jinja2, matplotlib, numpy, pandas, yaml"
python scripts/run-scan --help
```

Invoke scans as `python scripts/run-scan`: executing `scripts/run-scan` directly
selects `/usr/bin/python3`, which may differ from the activated environment.
For an existing scan configuration, `--dry-run` previews generation without
writing files. Some scan types, including likelihood profiles, need reference
fit outputs even for a preview. The [HERA study](hera-study.md) provides a
concrete eight-fit preview using the bundled inputs.

## Scientific runtime

The Python package does not install xFitter, HTCondor, ROOT, LHAPDF or theory
libraries. Use an xFitter build with the reactions and statistical features
required by your configuration. The repository supplies no xFitter binaries or
automated dependency build.

The supplied execution environment assumes Linux, CERN CVMFS and a shared
filesystem. Condor descriptors use `should_transfer_files = NO`: the checkout,
inputs and scientific installation must be accessible on worker nodes.

| Task | Additional requirements |
| --- | --- |
| Execute fits and scans | Built xFitter, the dependencies of the selected theory setup, HTCondor |
| Extract and plot scans | Completed scan outputs; Python plotting dependencies |
| Compare PDFs | Completed fit grids or PDF sets; Python LHAPDF bindings |
| Plot cross sections | Fit `fittedresults.txt` files, `xfitter-draw`, ROOT, Ghostscript, pdfLaTeX |
| Regional χ² tables through `scripts/plot-xsec` | Fit `fittedresults.txt` files and a working xFitter setup |

### Choose an installation and worktree

Edit the checkout's [`.env`](../.env). Its shipped paths describe the original
execution site; replace them with the shared paths of your installation. For
example, an installation could have this layout:

```text
/shared/xfitter/
├── setup.sh
├── deps/
└── builds/
    └── study-build/
        ├── .git
        ├── bin/xfitter
        └── lib/
```

The corresponding `.env` entries are below. Replace the commit placeholder
with the full lowercase 40-character revision you intend to use:

```bash
XFITTER_ROOT=/shared/xfitter
XFITTER_SETUP_ROOT=/shared/xfitter
XFITTER_TREE=builds/study-build
XFITTER_COMMIT="<full lowercase 40-character commit>"
```

`XFITTER_ROOT` contains the build trees. `XFITTER_SETUP_ROOT` contains the
installation's `setup.sh` and defaults to `XFITTER_ROOT` when unset.
`XFITTER_TREE` is a build-directory path, relative to `XFITTER_ROOT` or
absolute; it is not a branch name. The directory must already contain a built
`bin/xfitter`. Record the required revision with the study; setting a pin
checks an existing build and does not check out or compile it.

A study can also select its build in `config.yaml` or the worker text generated
by `condor/submit.sh`. Those explicit selections take precedence over `.env`.
If you locate a required build elsewhere, adapt its directory selection while
preserving the intended revision. The tested HERA build and additional theory
dependencies are documented separately in [HERA fits](hera-fits.md).

### Activate and check the runtime

In a new shell, after configuring `.env`:

```bash
source scripts/setup-env.sh
command -v xfitter
command -v condor_submit
```

The setup script reports the selected xFitter tree and checks a configured
commit pin. It rejects a different `HEAD` or tracked changes in the selected
xFitter tree; untracked build products do not invalidate the pin. Without
`XFITTER_COMMIT`, this revision check is not performed.

Before plotting, check the interpreter and components required by that task:

```bash
python3 -c "import matplotlib, numpy, pandas, yaml"
python3 -c "import lhapdf"       # PDF comparisons
command -v xfitter-draw         # cross-section plots
command -v root                 # cross-section plots
command -v gs                   # cross-section PDF assembly
command -v pdflatex             # cross-section PDF assembly
```

Scientific setup scripts can change `PATH` and Python library paths. Use a
Python environment compatible with the installed LHAPDF/ROOT libraries, and
install this package there if necessary. The isolated Python environment used
for command help does not automatically contain those compiled bindings.

### Environment overrides and site assumptions

Explicit caller or generated-worker `XFITTER_TREE` and `XFITTER_COMMIT` values
override `.env`. Selecting a tree without a commit suppresses the default-tree
pin; it does not infer the intended revision. To return an already configured
shell to the checkout defaults:

```bash
unset XFITTER_TREE XFITTER_COMMIT
source scripts/setup-env.sh
```

Changing `.env` does not rewrite study configurations or previously generated
workers. A generic `new-fit` launcher uses runtime defaults; a copied or
customized study launcher may contain an explicit build selection.

| Entry point | Environment behavior |
| --- | --- |
| Fit and scan workers | Source `scripts/setup-env.sh`; default LCG_105, EL9, GCC13 |
| `scripts/plot-scan` | Use available Python plotting modules, otherwise source LCG_106 |
| `scripts/plot-pdf-comparison` | Use available Python modules including LHAPDF, otherwise source LCG_106 |
| `scripts/plot-xsec` | Always initialize the selected xFitter build with `setup-env.sh` |

`XFITTER_LCG_SETUP` overrides the setup script's LCG view;
`LCG_SETUP` overrides the fallback view for scan/PDF plotting wrappers.
Generated fit workers also contain a CVMFS-specific OpenBLAS compatibility
shim. These overrides alone do not make the workers portable to a cluster
without CVMFS; adapt the execution environment and launchers for that site.

## Datasets and custom studies

For a single fit, `scripts/new-fit` accepts a custom configuration directory
and searches the full repository `datasets/` tree recursively by basename.
It copies only its supported configuration and data files; see
[fit creation](../runs/fits/README.md#create-a-workspace-from-your-inputs) for
handling additional inputs and the current default template.

The scan command has a narrower interface: `scripts/run-scan` currently fixes
its dataset root to `datasets/hera/h1zeusCombined/inclusiveDis/1506.06042` and
has no dataset-root option. The Python
[`run_scan` API](../src/xfitter_eoe_runs/scans/runner.py) accepts an explicit
`dataset_root`. Using it for other data requires compatible templates and a
review of the selected scan type's assumptions; changing that argument alone
does not generalize every parametrisation or likelihood-profile setting.

Continue with the [study catalog](../runs/README.md) for the workflow families
or the [HERA study](hera-study.md) for the supplied application. For software
checks, run `python -m unittest discover -s tests -v` in the environment where
the package is installed. These tests do not launch real xFitter or Condor jobs.
