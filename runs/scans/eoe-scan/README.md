# EoE-strength scans

[Workflows](../../README.md) · [Installation](../../../docs/installation.md) ·
[HERA Figure 1](../../../docs/hera-study.md#figure-1-common-epsilon)

Vary EoE strengths for a fixed set of sources, refitting the free parameters
at each point.

## Configuration

Create `runs/scans/eoe-scan/my-study/config.yaml`. All options:

```yaml
scan_type: lambda-scan
template: hera-baseline
dataset_root: /path/to/datasets
datafiles: [sample-a.dat, sample-b.dat]
epsilon: 0.6
lambda: {min: 0.0, max: 1.0, step: 0.1}
systematics:
  - {name: calibration, type: E, init: 0.0}
  - {name: normalization, type: E, epsilon: 0.3, scale_with_lambda: false}
  - {name: sysA, range: "1-4", type: E}
parameter_comparison:
  - {name: Bg, label: "$B_g$"}
n_iterations: 2
enable_bartlett: true
q2_cut: 3.5
doErrors: {method: Pumplin, errdef: 0.5, iterate: 10}
# plot_style: paper-common-epsilon
plot_font_size_offset: 0
xfitter_tree: xfitter-master
# xfitter_commit: <full 40-character commit>
request_memory: 2GB
```

- `scan_type` (required): `lambda-scan`.
- `template` (required): directory in `templates/` with the steering and
  parameter templates, constants and weights (`hera-baseline`, `giuli-param`,
  `bg-param-nnlo-nllx-fonll`).
- `dataset_root` (required): data directory, absolute or relative to
  `config.yaml`.
- `datafiles`: files copied from `dataset_root` into every fit.
- `epsilon`: default ε of every source; required unless each source sets
  its own.
- `lambda` (required): scan grid; each source's strength is `epsilon × lambda`.
  - `min`, `max`, `step`: grid limits and spacing. Points must differ at the
    first decimal, which names the fit directories. Include 0 for the
    parameter-reference plots.
- `systematics` (required): sources in every fit.
  - `name`: source name, as in the data files.
  - `type`: source type in xFitter's `ListOfSources`; `E` adds a nuisance
    parameter fitted by MINUIT.
  - `range`: optional `"first-last"`; expands `name` into numbered sources,
    e.g. `{name: sysA, range: "1-4"}` gives `sysA1` to `sysA4`.
  - `epsilon`: optional ε for this source, overriding the default.
  - `init`: optional starting value of an `E` nuisance; not allowed with `range`.
  - `scale_with_lambda` (default `true`): `false` keeps this source's ε fixed
    while λ varies.
- `parameter_comparison`: optional PDF parameters compared between λ = 0 and
  λ = 1; both points must be in the grid.
  - `name`: parameter name in the template.
  - `label` (default `name`): plot label; LaTeX is allowed.
- `n_iterations` (default `2`): iterations of xFitter's EoE nuisance profiling.
- `enable_bartlett` (default `true`): apply the Bartlett correction.
- `q2_cut` (default `3.5`): minimum Q² in GeV², for templates that read it
  (`bg-param-nnlo-nllx-fonll`); `hera-baseline` has a fixed cut at 3.5 GeV².
- `doErrors`: optional uncertainty method for the fits; omit it to use
  xFitter's default.
  - `method`: xFitter error method, e.g. `Pumplin`.
  - `errdef`, `iterate`: Pumplin `SET ERRDEF` and `ITERATE` values.
- `plot_style`: optional; `paper-common-epsilon` draws the χ² plot in the
  paper's Figure 1 format, with ε on the horizontal axis (use with `epsilon: 1`).
- `plot_font_size_offset` (default `0`): points added to plot font sizes.
- `xfitter_tree`, `xfitter_commit` (default from `.env`): xFitter build and
  required commit for the jobs; see
  [using your own build](../../fits/README.md#use-your-own-xfitter-build).
- `request_memory` (default `2GB`): Condor memory request per job.

[HERA configuration](herapdf20-nnlo-rtopt/common-epsilon/config.yaml).

## Run

```bash
workspace=runs/scans/eoe-scan/my-study
python scripts/run-scan --dry-run "$workspace"    # preview
python scripts/run-scan --no-submit "$workspace"  # generate
bash "$workspace/runs/submit.sh"                  # submit
# After the fits finish:
scripts/plot-scan "$workspace"
```

## Outputs

- `runs/lambda_<value>/`: generated fits.
- `results/chi2.csv`, `results/parameters.csv`: statistics and fitted parameters.
- `plots/1_chi2_vs_lambda.pdf`: Bartlett-corrected χ².
- Other PDFs in `plots/`: convergence, parameter values, errors and comparisons.
