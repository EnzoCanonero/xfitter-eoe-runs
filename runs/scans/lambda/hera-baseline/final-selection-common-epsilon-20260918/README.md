# FG common-epsilon scan: final seven-source HERA selection

Submitted on 2026-09-18 as HTCondor cluster **134382**, seven jobs, plus
**134383.0** for the subsequently requested epsilon=0.7 point: **eight jobs**.
The manuscript and its figures are not edited by this study.

The selected set is held fixed: sysHZComb1053, proc_tb21, sysHZComb1064,
sysHZComb1114, sysHZComb1144, sysHZComb1111, and sysHZComb1113.
All seven receive the same epsilon at each point: **0, 0.1, 0.2, 0.3, 0.4,
0.5, 0.6, 0.7**. All PDF parameters and selected NPs are refitted independently
at every point; the source list is not reselected.

The lambda-scan pipeline multiplies the configured base epsilon by lambda.
Here base epsilon is 1, so the numerical lambda coordinate is the physical
common epsilon. `lambda_0.6` is the original stress value, while
`lambda_0.0` gives Gaussian constraints. The initial proposed upper endpoint
of 1 was reduced to 0.6 at the user's request **before any jobs were
submitted**. The user then explicitly requested adding 0.7. That point was
generated and validated separately using the same pipeline helpers, and
submitted through `supplemental-epsilon-0.7/submit.sh`. The original seven
jobs and their running configs/scripts were neither regenerated nor resubmitted.
No jobs above 0.7 were submitted.

## Setup and validation

- Template: HERAPDF2.0 baseline, NNLO RTOPT/QCDNUM, Q0=sqrt(1.9) GeV,
  alpha_s(MZ)=0.118, original seven HERA inclusive datasets and Q2>=3.5 GeV2.
- All seven selected sources are explicit MINUIT `E` parameters, with the
  same seeds and ordering as the final selected fit. `SET PAR` supplies
  starts; no parameters are fixed by these commands.
- Bartlett enabled. Retain Pumplin ERRDEF=0.5 and ten iterations, providing
  PDF grids and uncertainty comparisons as well as raw/corrected chi2.
- The two profiling iterations affect only the remaining Gaussian sources;
  all seven EoE sources are minimised directly. At epsilon=0 the selected
  sources revert to ordinary quadratic penalties without division by zero.
- Explicit clean build pin: `xfitter-bartlett-fixes`, commit
  `00ba3ef836dedad4a06dd4d03ab152f413873887`, the maintained tree used by
  the retained HERA fits. Setup and loader checks passed. No repository
  default or shared build configuration was changed.
- Every generated data file, constants file and evolution weight matches
  the final selected fit. The full epsilon=0.6 steering and parameter cards
  match that fit except for output location and whitespace.
- All eight points have independent output directories. Shell syntax and
  HTCondor dry-run validation passed before submission.
- Resource request: one CPU and 2 GB per job.

`validation.json` records configuration/input checks and executable hashes.
`submission.json` maps cluster 134382 ProcId 0--6 to epsilon 0--0.6 and
134383.0 to epsilon 0.7. Every worker verifies
the selected clean Git pin and records that check in `condor/logs/error.log`.
This historical xFitter clears its output directory on startup, removing the
worker's initial in-output provenance/log files. The durable execution log
is therefore `condor/logs/output.log`; binary/library hashes are preserved
in the study's `validation.json`.

The historical executable prints raw NDF=1124 when seven NPs are explicit,
but uses the physical ndf=1131 and nPOI=14 for the Bartlett calculation.
Use the raw and corrected chi2 minima themselves; do not use the raw
printed reduced chi2 to compare with the paper's 1131 convention.
The epsilon=0 and 0.6 completed minima should be checked against the
archived baselines (1363.33 and raw1312.79/corrected1305.88), respectively.
Config validation and a clean startup do not establish final fit convergence.

## Monitoring and later extraction

From the repository root:

```bash
condor_q 134382 134383
scripts/plot-scan runs/scans/lambda/hera-baseline/final-selection-common-epsilon-20260918
```

The plotting pipeline uses the name lambda; for the requested chi2 plot its
numeric coordinate is epsilon and should be labelled accordingly. The scan
stops at epsilon=.7, so generic auxiliary plots assuming a lambda=1 point
are not applicable unchanged.

Local startup observations are saved in `monitoring/`. Startup monitoring
was stopped at the user's request. The temporary inspection helper has
been removed; no background monitor was started. The submission script
must not be rerun merely to check status, since that would submit another
batch.
