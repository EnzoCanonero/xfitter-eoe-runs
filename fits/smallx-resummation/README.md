# Small-x resummation fit matrix

This directory contains the controlled Gaussian fit matrix used to separate
the effects of the PDF input parametrisation and small-x resummation:

| Fit | PDF parametrisation | Perturbative setup |
|---|---|---|
| `herapdf-param-nnlo-fonll` | HERAPDF2.0 | NNLO APFEL/FONLL-C |
| `herapdf-param-nnlo-nllx-fonll` | HERAPDF2.0 | NNLO+NLLx APFEL/FONLL-C |
| `bg-param-nnlo-fonll` | Bonvini--Giuli | NNLO APFEL/FONLL-C |
| `bg-param-nnlo-nllx-fonll` | Bonvini--Giuli | NNLO+NLLx APFEL/FONLL-C |

Within each parametrisation pair the configurations are identical except for
`nllxResummation: "Off"` or `"On"`. All fits use the same seven combined HERA
inclusive datasets, cuts, multiplicative chi-square definition, starting
scale, masses and matching settings.

The worker script is pinned to the dedicated build
`xfitter-bartlett-apfel306-hell3`. No errors-on-errors sources are assigned in
this initial matrix; `Pumplin` is used only to obtain PDF confidence intervals.

Submission is intentionally guarded. The prepared sequence is to submit the
short NLLx environment smoke job first:

```bash
fits/smallx-resummation/smoke/submit.sh --submit
```

After that job has been checked, submit the four production fits with:

```bash
fits/smallx-resummation/gaussian/submit.sh --submit
```

The script patches each absolute output directory immediately before invoking
`condor_submit`.

## Pre-submission validation

The dedicated tree is built from commit `386c51eb3281`, with APFEL 3.0.6 and
HELL 3 tables loaded from the local dependency installation. The official
`paramBG` one-call test reproduces `1283.69/1127` with NLLx enabled; the same
point evaluated at fixed NNLO gives `1461.38/1127`.

Disposable one-call evaluations of the precise seeds used in these four cards
give:

| Parametrisation | NNLO | NNLO+NLLx |
|---|---:|---:|
| HERAPDF2.0 | `1772.25/1131` | `1498.09/1131` |
| Bonvini--Giuli | `1461.38/1127` | `1283.69/1127` |

These are starting-point evaluations, not minimised fit results. The precise
seeds are used because rounded Bonvini--Giuli logarithmic coefficients lie far
from the narrow published minimum. The HERAPDF seed is mapped from xFitter's
official `SmallxResummation` example; it has a very small negative high-x sea
at the starting scale, inherited from that example, which should be checked
again after minimisation.
