# Fit workspaces

[Workflows](../README.md) · [Installation](../../docs/installation.md) ·
[HERA figures](../../docs/hera-study.md)

One workspace contains an xFitter configuration, a Condor launcher and the fit
outputs.

## Create and configure

Create a new workspace from your xFitter input directory:

```bash
scripts/new-fit my-study/variant-a /absolute/path/to/template/config
```

An existing fit can supply the inputs instead:

```bash
scripts/new-fit my-study/variant-b my-study/variant-a/config
```

Creation does not submit a job. Edit the new workspace's:

- `config/steering.txt`: datasets, cuts and systematic sources.
- `config/parameters.yaml`: PDF parametrisation, theory and error calculation.
- `condor/submit.sh`: batch resources and any study-specific build selection.

The generator copies the main configuration files and finds referenced `.dat`
files by basename under `datasets/`. Add missing data or other auxiliary files
yourself. New launchers use the runtime from [`.env`](../../.env); they do not
inherit the source fit's launcher or build pin. Keep launcher changes in
`condor/submit.sh`, which regenerates the worker at submission.

## Run

```bash
workspace=runs/fits/my-study/variant-a
bash "$workspace/condor/submit.sh"
```

This submits immediately. The launcher sets `OutputDirectory`; leave its
generated placeholder in place.

## Use your own xFitter build

The supplied fits and scans record the xFitter build they were run with. In a
fit, `condor/submit.sh` contains:

```bash
export XFITTER_TREE=merge-master/xfitter-master
export XFITTER_COMMIT=67398b15571dff1e9ddce0bc88923554552c9c84
```

In a scan, `config.yaml` sets the same values as `xfitter_tree` and
`xfitter_commit`. If your build is elsewhere, the job stops before xFitter
starts, reporting `no built xfitter` or `commit mismatch`. Either:

- delete both lines (or fields) to use the build selected in `.env`; or
- point the tree at your build, relative to `XFITTER_ROOT` or absolute, and set
  the commit to its revision (`git -C /path/to/build rev-parse HEAD`). Delete
  the commit line if the build is not a Git checkout.

The commit check also fails if tracked files in the build have uncommitted
changes.

## Outputs

- `condor/logs/`: job logs.
- `output/Results.txt`, `minuit.out.txt`: fit statistics and minimizer output.
- PDF grids or LHAPDF sets: inputs for [PDF comparisons](../comparisons/pdf/README.md).
- `output/fittedresults.txt`: input for [cross-section comparisons](../comparisons/xsec/README.md).
