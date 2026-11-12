# EoE-strength scans

[Workflows](../../README.md) · [Installation](../../../docs/installation.md) ·
[HERA Figure 1](../../../docs/hera-study.md#figure-1-common-epsilon)

Vary EoE strengths for a fixed set of sources, refitting the free parameters
at each point. Previous fit outputs are not required.

## Configuration

Create `config.yaml` under `runs/scans/eoe-scan/my-study/`. Add the
[shared inputs](../../README.md#shared-scan-configuration) and these fields:

```yaml
scan_type: lambda-scan
epsilon: 0.6
lambda: {min: 0.0, max: 1.0, step: 0.1}
systematics:
  - {name: calibration, type: E, init: 0.0}
```

Replace the source name with one in your data.
[Complete HERA example](herapdf20-nnlo-rtopt/common-epsilon/config.yaml).

- Each source's strength is `epsilon × lambda`; a source can override
  `epsilon` or set `scale_with_lambda: false` to stay fixed.
- Include λ = 0 for the parameter-reference plots. Use grid values distinct
  at one decimal place, as used in generated directory names.
- Optional `parameter_comparison: [{name: Bg}]` compares selected parameters
  at λ = 0 and λ = 1; both points are needed.

## Run

From the repository root, after creating the configuration:

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

Check convergence and coverage of the requested grid before interpreting plots.
