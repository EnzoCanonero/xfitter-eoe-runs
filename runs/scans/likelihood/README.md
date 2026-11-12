# Profile-likelihood scans

[Repository](../../../README.md) · [Installation](../../../docs/installation.md) ·
[HERA examples](../../../docs/hera-scans.md#likelihood-profiles)

`scan_type: likelihood-scan` generates a nominal fit and a manual 1D or 2D
grid. At each grid point it fixes the selected parameters and refits the rest.
All fits use the same template, data, source settings and starting values.
No previous fit output is needed, including for a dry run.

## Configuration

Create `config.yaml` under `runs/scans/`. Use the usual `template`,
`dataset_root`, `datafiles`, `systematics`, `epsilon`, runtime and Condor settings.
PDF starting values and steps come from the template; `parameter_overrides`
changes them for every fit. E-type source starts use `systematics[].init`.

```yaml
scan_type: likelihood-scan
template: hera-baseline
dataset_root: /path/to/datasets
datafiles: [sample.dat]
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
  - pair: [Bg, calibration]
    x_range: [-0.3, 0.2]
    y_range: [-2, 2]
    npoints: [21, 15]
```

Replace the sample data and source names with your study's inputs. Supply at
least one scan list. Each 1D entry requires `min`, `max`, `npoints`; each 2D
entry requires `x_range`, `y_range` and `[nx, ny]` point counts. Bounds are
inclusive and grids are evenly spaced. PDF parameters must be free in the
nominal configuration; E-type parameters must be declared in `systematics`.
Their MINUIT indices follow the generated parameter and source declarations.

The parameter template can use numeric lists or value/step mappings, with
optional bounds. Dependent parameters cannot be scanned directly. E-source
commands are inserted before `call fcn 1` in the template's MINUIT commands.
`reference_fit`, `scan_defaults` and `n_sigma` are no longer supported.

## Run

From the repository root, with `workspace` set to your scan directory:

```bash
python scripts/run-scan --dry-run "$workspace"
python scripts/run-scan --no-submit "$workspace"
bash "$workspace/runs/submit.sh"
# After the fits finish:
scripts/plot-scan "$workspace"
```

Generation creates `runs/nominal/`, the grid fits, `runs/scan_manifest.json`
and the batch scripts. The nominal has no scan constraints and runs in the
same batch as the grid. Total jobs are **1 + all requested grid points**.
Generation requires an empty `runs/`; use a fresh workspace when changing a
study. Existing completed runs only need the plotting command. Old manifests
must be regenerated with the new configuration.

## Results

Extraction reads each fit's `output/Results.txt` and `output/minuit.out.txt`.
The nominal must have a finite raw minimized χ² and converged MIGRAD:

```text
delta_chi2 = chi2(point) - chi2(nominal)
```

This applies to every 1D and 2D point. There is no subtraction of a grid minimum
or central point, and no Bartlett correction. Negative differences are kept
and reported: check the nominal minimization if a converged point is lower.
Missing or failed points remain visible in CSV status fields and are excluded
from the profile curves. Axes use the configured parameter values.

Outputs are `results/profiles_1d.csv`, `plots/profiles_1d.pdf`,
`results/grids_2d.csv`, `plots/likelihood_2d_convergence.pdf` and
`plots/likelihood_2d_profiles.pdf`, as requested. CSVs include `nominal_chi2`.
The 2D `results/quadratic_fit_summary.txt` uses raw parameter coordinates.
Check grid coverage and convergence before interpreting intervals.
