# Three informed PDF sets for Section 6

Compares the HERAPDF2.0 (RTOPT), Bonvini–Giuli (RTOPT), and Bonvini–Giuli
NNLO+NLLx FONLL-C informed fits at Q² = 4 GeV². All three assign epsilon=0.6
to the seven procedural sources, epsilon=0.3 to the forty HERA pull-study
sources (including sysHZComb1053), and zero to the remaining sources.

The archived lambda_0.5 scan points are the nominal informed fits in the
paper: in those scans only epsilon_1053 varies as 0.6*lambda. Their corrected
minima are 1327.66, 1276.02 and 1266.90. The stand-alone hera-pull-weighted
fits instead use epsilon_1053=0.6 and must not be substituted here.

The comparison reads native central and Pumplin +/- grids from the explicit
20260818 archives. It retains all 16, 19 and 19 error directions, respectively.
The grids already include the confidence-interval correction; no additional
Bartlett scaling is applied by this plotting stage. Bands use the same
symmetric prescription as the existing PDF figures.

All three curves are informed fits. The ratio denominator is the informed
HERAPDF2.0 central PDF, without denominator-error propagation. The reference
band shows its own relative PDF uncertainty.

The unchanged comparison script provides 12-by-6-inch pages, ticks at 16 pt,
axis labels and titles at 20 pt, and legends at 13 pt. Ratio ranges are automatic
to show the full differences between physics setups. The paper-style preview
arranges the three absolute panels above the corresponding ratio panels by
placing the left and right halves of the existing PDF pages without rescaling
their contents.

Run from the repository root:

```bash
scripts/plot-pdf-comparison runs/comparisons/informed-three-set-20260818
```

No fit jobs are submitted and the manuscript is not modified.
