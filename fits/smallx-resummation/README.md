# Small-x resummation fits

This directory contains the three small-x configurations retained for the
paper:

| Fit | Uncertainty treatment | Perturbative setup |
|---|---|---|
| `gaussian/bg-param-nnlo-fonll` | Gaussian baseline | NNLO APFEL/FONLL-C |
| `gaussian/bg-param-nnlo-nllx-fonll` | Gaussian baseline | NNLO+NLLx APFEL/FONLL-C |
| `eoe/bg-param-nnlo-nllx-fonll-greedy-top5` | Five greedy-selected EoE sources | NNLO+NLLx APFEL/FONLL-C |

The two Gaussian configurations use the same Bonvini--Giuli parametrisation
and differ only by `nllxResummation: "Off"` or `"On"`. The EoE configuration
uses the resummed setup with the five-source greedy selection from the paper.
All fits use the same seven combined HERA inclusive datasets, cuts,
multiplicative chi-square definition, starting scale, masses and matching
settings.

The worker scripts are pinned to the dedicated build
`xfitter-bartlett-apfel306-hell3`. `Pumplin` is used to obtain PDF confidence
intervals. Submission remains guarded by the `--submit` flag in the Gaussian
and EoE submit helpers; no smoke configuration is part of the active matrix.

## Pre-submission validation

The dedicated tree is built from commit `00ba3ef836de`, with APFEL 3.0.6 and
HELL 3 tables loaded from the local dependency installation. The official
`paramBG` one-call test reproduces `1283.69/1127` with NLLx enabled; the same
point evaluated at fixed NNLO gives `1461.38/1127`.

Disposable one-call evaluations of the precise Bonvini--Giuli seeds give
`1461.38/1127` at NNLO and `1283.69/1127` at NNLO+NLLx.

These are starting-point evaluations, not minimised fit results. The precise
seeds are used because rounded Bonvini--Giuli logarithmic coefficients lie far
from the narrow published minimum.
