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

The supplied fits and scans use xFitter master. In a fit, `condor/submit.sh`
contains:

```bash
export XFITTER_TREE=merge-master/xfitter-master
# export XFITTER_COMMIT=aead2b830305623b73709f748a4db918a0bf136c
```

In a scan, `config.yaml` sets the same values as `xfitter_tree` and a commented
`xfitter_commit`. The job uses whatever commit the tree is checked out at. If
your build is elsewhere, the job stops before xFitter starts, reporting
`no built xfitter`. Either:

- delete the tree line (or field) to use the build selected in `.env`; or
- point the tree at your build, relative to `XFITTER_ROOT` or absolute.

To require an exact revision, uncomment the commit line and set it to the
build's full commit (`git -C /path/to/build rev-parse HEAD`). The job then
stops if the build is at another commit (`commit mismatch`) or has uncommitted
changes to tracked files.

The EoE fit outputs were produced with xFitter `67398b15`, as recorded in their
Condor logs; the Gaussian fits record no build. In the fitting code, `67398b15`
differs from the merged master only in how zero-prior `:N` sources count
towards the degrees of freedom; these fits have none. Scan configurations with a
build note list what has not been run on master.

## Outputs

- `condor/logs/`: job logs.
- `output/Results.txt`, `minuit.out.txt`: fit statistics and minimizer output.
- PDF grids or LHAPDF sets: inputs for [PDF comparisons](../comparisons/pdf/README.md).
- `output/fittedresults.txt`: input for [cross-section comparisons](../comparisons/xsec/README.md).
