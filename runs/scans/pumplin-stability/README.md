# Pumplin uncertainty stability

[Workflows](../../README.md) · [Installation](../../../docs/installation.md)

Compare uncertainty intervals while varying EoE strengths and Pumplin's
`ERRDEF` and `ITERATE`.

## Configuration

Create `runs/scans/pumplin-stability/my-study/config.yaml`. All options:

```yaml
scan_type: pumplin-stability
template: hera-baseline
dataset_root: /path/to/datasets
datafiles: [sample-a.dat, sample-b.dat]
eps: 0.6
lambda: [0.5, 1.0]
errdef: [0.5, 1.0]
iterate: [10, 20]
errdef_ref: 0.5
systematics:
  - {name: calibration, type: E, init: 0.0}
  - {name: normalization, type: E, epsilon: 0.3}
plot_parameters: [Bg, Cg]
n_iterations: 2
enable_bartlett: true
q2_cut: 3.5
xfitter_tree: xfitter-master
# xfitter_commit: <full 40-character commit>
request_memory: 2GB
```

The scan runs every combination of `lambda`, `errdef` and `iterate`.

- `scan_type` (required): `pumplin-stability`.
- `template` (required): directory in `templates/` with the steering and
  parameter templates, constants and weights (`hera-baseline`, `giuli-param`,
  `bg-param-nnlo-nllx-fonll`).
- `dataset_root` (required): data directory, absolute or relative to
  `config.yaml`.
- `datafiles`: files copied from `dataset_root` into every fit.
- `eps` (required): default ε of every source.
- `lambda` (required): nonzero λ values; each source's strength is ε × λ. A
  Gaussian λ = 0 group is added automatically.
- `errdef` (required): Pumplin `SET ERRDEF` values.
- `iterate` (required): Pumplin `ITERATE` values.
- `errdef_ref` (default `0.5`): `ERRDEF` used as reference in the invariance plot.
- `systematics` (required): sources in every λ > 0 fit.
  - `name`: source name, as in the data files.
  - `type`: source type in xFitter's `ListOfSources`; `E` adds a nuisance
    parameter fitted by MINUIT.
  - `range`: optional `"first-last"`; expands `name` into numbered sources,
    e.g. `{name: sysA, range: "1-4"}` gives `sysA1` to `sysA4`.
  - `epsilon`: optional ε for this source, overriding the default.
  - `init`: optional starting value of an `E` nuisance; not allowed with `range`.
- `plot_parameters` (required): PDF parameters shown in the diagnostics; `E`
  nuisances are added automatically.
- `n_iterations` (default `2`): iterations of xFitter's EoE nuisance profiling,
  separate from Pumplin's `ITERATE`.
- `enable_bartlett` (default `true`): apply the Bartlett correction.
- `q2_cut` (default `3.5`): minimum Q² in GeV², for templates that read it
  (`bg-param-nnlo-nllx-fonll`); `hera-baseline` has a fixed cut at 3.5 GeV².
- `xfitter_tree`, `xfitter_commit` (default from `.env`): xFitter build and
  required commit for the jobs; see
  [using your own build](../../fits/README.md#use-your-own-xfitter-build).
- `request_memory` (default `2GB`): Condor memory request per job.

`doErrors` is set by the scan grid and is not read from the configuration.
[HERA configuration](herapdf20-nnlo-rtopt/eoe-selected/config.yaml).

## Run

```bash
workspace=runs/scans/pumplin-stability/my-study
python scripts/run-scan --dry-run "$workspace"    # preview
python scripts/run-scan --no-submit "$workspace"  # generate
bash "$workspace/runs/submit.sh"                  # submit
# After the fits finish:
scripts/plot-scan "$workspace"
```

## Outputs

- `results/pumplin_widths.csv`: interval half-widths from generated MINUIT logs.
- `plots/pumplin_iteration_convergence.pdf`: ratios to the largest available `ITERATE`.
- `plots/pumplin_errdef_invariance.pdf`: ratios to `errdef_ref` (or an available fallback).
- Eigenmode CSVs and plots when the fit logs contain covariance information.
