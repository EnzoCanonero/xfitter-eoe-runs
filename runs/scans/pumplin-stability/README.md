# Pumplin uncertainty stability

[Workflows](../../README.md) · [Installation](../../../docs/installation.md)

Compare uncertainty intervals while varying EoE strengths and Pumplin's
`ERRDEF` and `ITERATE`. The scan generates its own fits.

## Configuration

Create `config.yaml` under `runs/scans/pumplin-stability/my-study/`. Add the
[shared inputs](../../README.md#shared-scan-configuration) and these fields:

```yaml
scan_type: pumplin-stability
eps: 0.6
lambda: [0.5, 1.0]
errdef: [0.5, 1.0]
iterate: [10, 20]
errdef_ref: 0.5
systematics:
  - {name: calibration, type: E, init: 0.0}
plot_parameters: [Bg, Cg]
```

Replace the source and parameter names with those in your study.
[Complete HERA example](herapdf20-nnlo-rtopt/eoe-selected/config.yaml).

- The grid crosses all λ, `errdef` and `iterate` values. A Gaussian λ = 0
  group is added automatically; list only nonzero λ values.
- Each source's strength is its ε multiplied by λ; `eps` sets the default ε.
- `iterate` controls Pumplin errors; `n_iterations` controls nuisance profiling.
- `plot_parameters` is required. E-type nuisances are added to the plots.

## Run

From the repository root, after creating the configuration:

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

Check that fits converged and the requested settings are present before
interpreting the stability ratios.
