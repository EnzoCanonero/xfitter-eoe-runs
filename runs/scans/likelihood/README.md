# Likelihood profiles

[Workflows](../../README.md) · [Installation](../../../docs/installation.md)

Generate a nominal fit and a manual 1D or 2D grid. Each grid point fixes the
selected parameters and refits the rest.

## Configuration

Create `runs/scans/likelihood/my-study/config.yaml`. All options:

```yaml
scan_type: likelihood-scan
template: hera-baseline
dataset_root: /path/to/datasets
datafiles: [sample-a.dat, sample-b.dat]
epsilon: 0.6
systematics:
  - {name: calibration, type: E, init: 0.0}
parameter_overrides:
  Bg: {value: -0.06, step: 0.02}
scan_params_1d:
  - {name: Bg, min: -0.3, max: 0.2, npoints: 31}
scan_systematics_1d:
  - {name: calibration, min: -2, max: 2, npoints: 21}
scan_params_2d:
  - {pair: [Bg, calibration], x_range: [-0.3, 0.2], y_range: [-2, 2], npoints: [21, 15]}
n_iterations: 2
enable_bartlett: true
q2_cut: 3.5
# doErrors: {method: Pumplin, errdef: 0.5, iterate: 10}
xfitter_tree: xfitter-master
# xfitter_commit: <full 40-character commit>
request_memory: 2GB
```

- `scan_type` (required): `likelihood-scan`.
- `template` (required): directory in `templates/` with the steering and
  parameter templates, constants and weights (`hera-baseline`, `giuli-param`,
  `bg-param-nnlo-nllx-fonll`).
- `dataset_root` (required): data directory, absolute or relative to
  `config.yaml`.
- `datafiles`: files copied from `dataset_root` into every fit.
- `epsilon`: default ε of every source; required unless each source sets
  its own.
- `systematics` (default empty, Gaussian fits): sources in every fit. Their
  `E` nuisances can be scanned.
  - `name`: source name, as in the data files.
  - `type`: source type in xFitter's `ListOfSources`; `E` adds a nuisance
    parameter fitted by MINUIT.
  - `range`: optional `"first-last"`; expands `name` into numbered sources,
    e.g. `{name: sysA, range: "1-4"}` gives `sysA1` to `sysA4`.
  - `epsilon`: optional ε for this source, overriding the default.
  - `init`: optional starting value of an `E` nuisance; not allowed with `range`.
- `parameter_overrides`: optional starting values for template PDF parameters,
  applied to every fit.
  - `<parameter>`: `value` and/or `step`.
- `scan_params_1d`: 1D scans of PDF parameters, which must be free in the
  nominal fit.
  - `name`: parameter name.
  - `min`, `max`: grid limits, both included.
  - `npoints`: number of evenly spaced points, at least 2.
- `scan_systematics_1d`: 1D scans of `E` nuisances declared in `systematics`;
  same entries as `scan_params_1d`.
- `scan_params_2d`: 2D scans.
  - `pair`: `[x, y]`, PDF parameters or `E` nuisances.
  - `x_range`, `y_range`: `[min, max]` for each axis.
  - `npoints`: `[nx, ny]`.
- `n_iterations` (default `2`): iterations of xFitter's EoE nuisance profiling.
- `enable_bartlett` (default `true`): apply the Bartlett correction.
- `q2_cut` (default `3.5`): minimum Q² in GeV², for templates that read it
  (`bg-param-nnlo-nllx-fonll`); `hera-baseline` has a fixed cut at 3.5 GeV².
- `doErrors`: optional uncertainty method for the fits; omit it to use
  xFitter's default.
  - `method`: xFitter error method, e.g. `Pumplin`.
  - `errdef`, `iterate`: Pumplin `SET ERRDEF` and `ITERATE` values.
- `xfitter_tree`, `xfitter_commit` (default from `.env`): xFitter build and
  required commit for the jobs; see
  [using your own build](../../fits/README.md#use-your-own-xfitter-build).
- `request_memory` (default `2GB`): Condor memory request per job.

At least one scan list is required.
[HERA configuration](herapdf20-nnlo-rtopt/eoe-selected/config.yaml).

## Run

```bash
workspace=runs/scans/likelihood/my-study
python scripts/run-scan --dry-run "$workspace"    # preview
python scripts/run-scan --no-submit "$workspace"  # generate
bash "$workspace/runs/submit.sh"                  # submit
# After the fits finish:
scripts/plot-scan "$workspace"
```

The batch contains `runs/nominal/` plus all grid points. Generation requires
an empty `runs/`; use a new workspace when changing the scan.

## Outputs and reference

**Δχ² = χ²(point) − χ²(nominal)** for every 1D and 2D point, using raw χ²
without Bartlett correction. The reference is always the nominal fit, never
the lowest scan point. The nominal must converge; negative differences are
retained and reported. Failed points are flagged in CSVs and excluded from curves.

- `results/profiles_1d.csv`, `plots/profiles_1d.pdf`: 1D profiles.
- `results/grids_2d.csv`, `plots/likelihood_2d_profiles.pdf`: 2D profiles.
- `plots/likelihood_2d_convergence.pdf`: 2D fit status.

Both CSVs include `nominal_chi2`.
