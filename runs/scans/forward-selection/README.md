# Systematic-source ranking

[Workflows](../../README.md) · [Installation](../../../docs/installation.md)

Fit a base configuration and test one additional EoE source at a time.
Each round generates its own fits; no previous round's outputs are needed.

## Configuration

Create `config.yaml` under `runs/scans/forward-selection/my-study/`. Add the
[shared inputs](../../README.md#shared-scan-configuration) and these fields:

```yaml
scan_type: systematic-ranking
epsilon: 0.6
base_systematics: []
systematics:
  - {name: calibration, type: E}
  - {name: normalization, type: E}
```

Replace the source names with candidates from your data.
[Complete HERA example](herapdf20-nnlo-rtopt/epsilon-0p6/round-01/config.yaml).

- `base_systematics`: sources active in every fit; empty gives a Gaussian base.
- `systematics`: candidates to test; sources already in the base are skipped.
- For the next round, add the chosen source to `base_systematics` in a new
  workspace. Selection and stopping are manual.

## Run

From the repository root, after creating the configuration:

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

`dchi2_corrected = chi2_corrected(base) - chi2_corrected(candidate)`; larger
values mean greater improvement. Check `base_converged` and `non_converged`
before choosing a source: failed fits can still appear in the ranking.
