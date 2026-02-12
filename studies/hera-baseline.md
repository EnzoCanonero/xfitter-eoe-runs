# HERA baseline study

## Scope
Baseline HERA inclusive fit variants used for EoE studies.

## Fit variants

- `fits/hera/hera-baseline/eoe`: baseline EoE setup (reference).
- `fits/hera/hera-baseline/nominal`: EoE disabled (`&Systematics` has no EoE source list/iterations/Bartlett).
- `fits/hera/hera-baseline/eoe-no-bartlett`: same as EoE baseline, but `Enable_Bartlett = .false.`.

## Notes

- All variants are derived from the same base config (`hera/hera-baseline/eoe`).
- Runtime outputs are intentionally not tracked by Git (`output/`, `condor/logs/`).

## Typical run

```bash
cd fits/hera/hera-baseline/eoe
condor_submit condor/job.sub
```
