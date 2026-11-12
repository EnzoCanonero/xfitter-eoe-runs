# Likelihood profiles

[Workflows](../../README.md) · [Installation](../../../docs/installation.md)

Generate a nominal fit and a manual 1D or 2D grid. Each grid point fixes the
selected parameters and refits the rest. No previous fit output is needed.

## Configuration

Create `config.yaml` under `runs/scans/likelihood/my-study/`. Add the
[shared inputs](../../README.md#shared-scan-configuration) and these fields:

```yaml
scan_type: likelihood-scan
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

Replace names and ranges for your study; keep at least one scan list.
[Complete HERA example](herapdf20-nnlo-rtopt/eoe-selected/config.yaml).

- Grids are evenly spaced, including both bounds. PDF parameters must be free
  in the nominal fit; E-type nuisances must be declared in `systematics`.
- PDF starts come from the template; optional `parameter_overrides` changes
  values and steps. Source starts use `init`. These settings apply to all fits.

## Run

From the repository root, after creating the configuration:

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
