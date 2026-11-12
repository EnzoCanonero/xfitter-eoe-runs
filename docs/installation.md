# Installation and environment

[Repository](../README.md) · [Workflow guides](../runs/README.md) ·
[Fit workspaces](../runs/fits/README.md) · [HERA and paper figures](hera-study.md)

Run the commands below in Bash from the repository root.

## Get the documented checkout

The commands and layout documented here are on
`compat/errors-on-errors-20260903`:

```bash
git clone --branch compat/errors-on-errors-20260903 \
  https://github.com/EnzoCanonero/xfitter-eoe-runs.git
cd xfitter-eoe-runs
```

The checkout includes configurations and tools, but no fit outputs or plots.

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
writing files. Likelihood scans also prepare their own nominal fit and need
no previous fit outputs. The [HERA guide](hera-study.md) provides a
concrete eight-fit preview using the bundled inputs.

## xFitter installation

Follow the official [xFitter installation guide](https://gitlab.cern.ch/fitters/xfitter/-/wikis/Installation-script)
for xFitter and its theory dependencies. Use a build with the errors-on-errors
features required by your study.

## Environment setup

Edit [`.env`](../.env) to match your installation, for example:

```bash
XFITTER_ROOT=/shared/xfitter
XFITTER_SETUP_ROOT=/shared/xfitter
XFITTER_TREE=xfitter-master
XFITTER_COMMIT=
```

`XFITTER_SETUP_ROOT` contains the installer's `setup.sh`. `XFITTER_TREE` is the
built directory under `XFITTER_ROOT` (or an absolute path), containing
`bin/xfitter`. Leave `XFITTER_COMMIT` empty, or set it to the full 40-character
Git commit to require that revision. Study configurations and generated workers
can override the selected build.

Load the runtime in each new shell:

```bash
source scripts/setup-env.sh
command -v xfitter
```

The supplied setup and workers use CERN LCG through CVMFS. Batch jobs require
the repository, inputs and installation at the same shared paths on worker
nodes. Adapt the setup and worker scripts for other sites.

## Additional dependencies

Beyond the xFitter installer and this Python package:

- **HTCondor** is needed to submit fit and scan jobs.
- **LHAPDF Python bindings** are needed for PDF comparisons. The xFitter
  installer builds LHAPDF with Python disabled; use bindings provided by your
  LCG environment or a build with Python support. Check with
  `python3 -c "import lhapdf"` in the environment used for plotting.
- **ROOT** is needed for `xfitter-draw`; use the site's LCG environment or a
  separate ROOT installation.
- **Ghostscript** (`gs`) assembles `xfitter-draw`'s combined PDF output;
  `ps2pdf` is used for its optional `--splitplots-pdf` output.
- **LaTeX** (`pdflatex`) compiles `xfitter-draw`'s summary tables, unless
  disabled with `--no-tables`.

Use a Python interpreter compatible with the scientific libraries; loading the
runtime can change the interpreter selected by `PATH`.

Continue with the [workflow guides](../runs/README.md) or the
[HERA and paper figures](hera-study.md).
