# Systematic-source ranking

[Workflows](../../README.md) · [Installation](../../../docs/installation.md)

Fit a base configuration and test one additional EoE source at a time.

## Configuration

Create `runs/scans/forward-selection/my-study/config.yaml`. All options:

```yaml
scan_type: systematic-ranking
template: hera-baseline
dataset_root: /path/to/datasets
datafiles: [sample-a.dat, sample-b.dat]
epsilon: 0.6
base_systematics:
  - {name: calibration, type: E, init: -1.2}
systematics:
  - {name: normalization, type: E}
  - {name: sysA, range: "1-40", type: E}
n_iterations: 2
enable_bartlett: true
q2_cut: 3.5
doErrors: {method: Pumplin, errdef: 0.5, iterate: 10}
xfitter_tree: xfitter-master
# xfitter_commit: <full 40-character commit>
request_memory: 2GB
```

- `scan_type` (required): `systematic-ranking`.
- `template` (required): directory in `templates/` with the steering and
  parameter templates, constants and weights (`hera-baseline`, `giuli-param`,
  `bg-param-nnlo-nllx-fonll`).
- `dataset_root` (required): data directory, absolute or relative to
  `config.yaml`.
- `datafiles`: files copied from `dataset_root` into every fit.
- `epsilon`: default ε of every source; required unless each source sets
  its own.
- `base_systematics` (default empty): sources in every fit, including the
  nominal; empty gives a Gaussian nominal. Same entries as `systematics`.
- `systematics` (required): candidates, one fit each; sources already in
  `base_systematics` are skipped.
  - `name`: source name, as in the data files.
  - `type`: source type in xFitter's `ListOfSources`; `E` adds a nuisance
    parameter fitted by MINUIT.
  - `range`: optional `"first-last"`; expands `name` into numbered sources,
    e.g. `{name: sysA, range: "1-4"}` gives `sysA1` to `sysA4`.
  - `epsilon`: optional ε for this source, overriding the default.
  - `init`: optional starting value of an `E` nuisance; not allowed with `range`.
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

For the next round, add the chosen source to `base_systematics` in a new
workspace; selection and stopping are manual.
[HERA configuration](herapdf20-nnlo-rtopt/epsilon-0p6/round-01/config.yaml).

## Run

```bash
workspace=runs/scans/forward-selection/my-study
python scripts/run-scan --dry-run "$workspace"    # preview
python scripts/run-scan --no-submit "$workspace"  # generate
bash "$workspace/runs/submit.sh"                  # submit
# After the fits finish:
scripts/plot-scan "$workspace"
```

## Outputs

- `runs/nominal/`, `runs/<source>/`: base and candidate fits.
- `results/rankings.csv`: candidates ordered by improvement in corrected χ².
- `results/chi2.csv`, `results/parameters.csv`: fit statistics and parameters.
- `plots/chi2_ranking.pdf`, `plots/parameters.pdf`: diagnostic plots.

`dchi2_corrected = chi2_corrected(base) - chi2_corrected(candidate)`. Failed
fits still appear in the ranking; see `base_converged` and `non_converged`.
