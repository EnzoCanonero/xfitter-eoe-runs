# Installation and environment

[Repository](../README.md) · [Workflow guides](../runs/README.md) ·
[Fit workspaces](../runs/fits/README.md) · [HERA and paper figures](hera-study.md)

Run the commands below in Bash from the repository root.

## Python installation

Install the package with Python 3.9 or newer:

```bash
python -m pip install .
python scripts/run-scan --help
```

This installs Jinja2, matplotlib, NumPy, pandas and PyYAML, and shows the scan
command's options without creating files or submitting jobs.

## xFitter installation

Follow the official [xFitter installation guide](https://gitlab.cern.ch/fitters/xfitter/-/wikis/Installation-script)
for xFitter and its theory dependencies. Use xFitter master at or after merge
commit `aead2b830305623b73709f748a4db918a0bf136c` (merge request !407), which
includes errors-on-errors.

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
