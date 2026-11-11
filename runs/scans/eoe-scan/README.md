# EoE-strength scans

[Repository](../../../README.md) · [Installation](../../../docs/installation.md) ·
[HERA study](../../../docs/hera-study.md) ·
[HERA examples](../../../docs/hera-scans.md#eoe-strength-scans) ·
[Paper reproduction](../../../docs/reproducing-paper.md)

`scan_type: lambda-scan` varies EoE strengths for a fixed list of systematic
sources. Other free parameters are refitted at every point. It measures the
response of a specified assignment; it does not repeat
[source selection](../forward-selection/README.md) at each strength.

## Configuration and inputs

Create a workspace under `runs/scans/` with a `config.yaml` containing:

| Field | Meaning |
| --- | --- |
| `scan_type` | `lambda-scan` |
| `template` | Directory name under root `templates/` |
| `dataset_root` | Dataset directory, relative to the directory containing `config.yaml`; absolute and `~` paths also work |
| `datafiles` | Dataset filenames copied into generated fits |
| `lambda` | Mapping with `min`, `max`, `step` for the scan grid |
| `systematics` | Source entries: `name`, `type`, optional `range`, `epsilon`, `init`, `scale_with_lambda` |
| `epsilon` | Default source strength when not specified per entry |
| `n_iterations`, `enable_bartlett`, `q2_cut` | Options passed to the steering template |
| `doErrors` | Optional error method; Pumplin accepts `errdef` and `iterate` |
| `parameter_comparison` | Optional ordered list of `{name, label}` entries for the λ = 0/1 comparison; `label` defaults to `name` |
| `xfitter_tree`, `xfitter_commit` | Worker build directory and optional exact revision |
| `request_memory` | Condor memory request |

For a scaled source, the physical strength is `epsilon_source × lambda`.
`scale_with_lambda` defaults to `true`; setting it to `false` keeps that
source's strength fixed. At least one source must be scaled. Source `init`
values are starting values, not fixed nuisance shifts. Source declarations
remain present at λ = 0, even when their constraints become Gaussian.

Choose a grid with distinct one-decimal λ values: generated directory names
use `lambda_<value>` formatted to one decimal. The generator passes the configured
sources to the selected steering template and uses its parameter, constants
and weight files. It does not require a reference-fit output.

`scripts/run-scan` copies `datafiles` from the configured `dataset_root`.
The library `run_scan` uses that root when its `dataset_root` argument is
`None`; an explicit path overrides it. For example, these configuration fields
select data and two parameters from your study:

```yaml
dataset_root: ../sample-data
datafiles: [sample-a.dat, sample-b.dat]
parameter_comparison:
  - {name: shape_a, label: '$a$'}
  - {name: shape_b}
```

Use parameter names present in your fit outputs. Omit `parameter_comparison`
or set it to `[]` to disable the optional comparison plot. Other scan fields
are still required as described above.

## Commands

Set `workspace` to **your existing configuration directory** under `runs/scans/`.
The commands below are a template for that workspace; configured, runnable
examples are in the [HERA scan guide](../../../docs/hera-scans.md#eoe-strength-scans).
Run from the repository root after installation.

Preview the grid without writing files:

```bash
python scripts/run-scan --dry-run "${workspace:?Set workspace to your scan directory}"
```

Generate inputs without submitting:

```bash
python scripts/run-scan --no-submit "${workspace:?Set workspace to your scan directory}"
```

Submit the generated batch:

```bash
bash "${workspace:?Set workspace to your scan directory}/runs/submit.sh"
```

After fitting, extract and plot:

```bash
scripts/plot-scan "${workspace:?Set workspace to your scan directory}"
```

Generation writes the workspace's `runs/` tree. Use another workspace for a
changed study; existing fit outputs need only the plotting command. Omitting
both scan flags generates and submits immediately.

## Outputs and plotting limits

Each point lives under `runs/lambda_<value>/`. Its `output/` contains
`Results.txt`, `minuit.out.txt`, `xfitter_run.log` and
`xfitter_provenance.txt`. `runs/batch/fit_dirs.txt` records the generated
inventory and `runs/batch/batch.log` records submitted Condor events.

Extraction writes `results/chi2.csv` and `results/parameters.csv`.
The standard plots beneath `plots/` are:

- `1_chi2_vs_lambda.pdf`: Bartlett-corrected goodness of fit.
- `2_convergence_status.pdf`: convergence counts for extracted points.
- `3_parameter_central_values.pdf` and `4_parameter_errors.pdf`: parameter
  changes relative to the λ = 0 fit.
- `5_parameter_profiles.pdf` and `6_parameter_pulls.pdf`: parameter diagnostics.
- `7_parameter_comparison.pdf`: an optional comparison of the configured
  `parameter_comparison` entries, in their listed order, at λ = 0 and λ = 1.

The generic parameter diagnostics use a λ = 0 reference, so include it for
those plots. The seventh plot requires both λ = 0 and λ = 1 with every selected
parameter and is skipped when any are absent. It scales the λ = 1 intervals
by that fit's Bartlett confidence-interval factor, using 1 when unavailable.
`plot_style` and `plot_font_size_offset` affect presentation;
`paper-common-epsilon` assumes the scan coordinate is physical common ε.
The [HERA guide](../../../docs/hera-scans.md#eoe-strength-scans) explains that
specific configuration.

Compare extracted coordinates and row counts with the generated grid, and
inspect `converged` and corrected χ². Missing or invalid results may be
omitted. A plot or its convergence-count panel alone does not establish that
all requested fits completed.
