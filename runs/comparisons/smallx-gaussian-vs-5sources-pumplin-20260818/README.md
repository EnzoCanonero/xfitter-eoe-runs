# Candidate Figure 4: resummed Gaussian versus errors-on-errors

Prepared on 2026-09-18 for review before changing the paper. Following user
approval, the candidate Figure 4 was installed in
`eoe_pdf_paper_2026_09_18_part_B` and the paper was rebuilt. The implemented
paragraph drops the final comparison between configurations and gives
more emphasis to selective broadening of the valence confidence intervals.
Source changes are confined to the PDF discussion and Figure 4 caption
in Section 5. The previous source, paper PDF and Figure 4 assets are saved
under that paper's `.b03_revision/figure4-gaussian-eoe-20260918` directory.

## Archived inputs

`inputs/gaussian/output` and `inputs/eoe/output` link explicitly to the
requested 20260818 archives. Absolute paths are recorded in
`input-provenance.json`:

- Gaussian: `runs/fits/smallx-resummation/gaussian/bg-param-nnlo-nllx-fonll/output_retained_premerge_20260818`
- EoE: `runs/fits/smallx-resummation/eoe/bg-param-nnlo-nllx-fonll-greedy-top5/output_legacy_premerge_20260818`

No fits were rerun and no archived outputs were edited. The comparison
uses NNLO+NLLx FONLL-C on both sides, not the fixed-order FONLL-C control
and not the BG RTOPT EoE fit used in the previous Figure 4.

## Consistency checks

- Both archived fits use the same recorded xFitter binary and APFEL 3.0.6,
  the Bonvini--Giuli parametrisation, NNLO+NLLx FONLL-C, the same seven
  datasets and cuts, Q0 = 1.6 GeV, mc = 1.46 GeV, muc = 1.12 mc, and
  alpha_s(MZ) = 0.118. The differences are the EoE treatment and fit seeds.
- The five EoE sources are sysHZComb1053, sysHZComb1062, sysHZComb1111,
  sysHZComb1114, and sysHZComb1144, all with epsilon = 0.6.
- Gaussian minimum: 1283.49. EoE raw minimum: 1251.65; Bartlett-corrected
  minimum: 1246.91. These agree with the manuscript's rounded minima.
- Both final MIGRAD fits converged, report accurate error matrices, and
  have OK status. Final EDMs are 0.58e-5 (Gaussian) and 0.39e-6 (EoE).
  Initial HESSE warnings do not describe the final error matrices.
- Ten Pumplin iterations finish with positive eigenvalues in both fits.
  At Q2 = 4 GeV2 the grids are indexed `_04.txt`, with 101 native x points.
  All 18 Gaussian and 23 EoE plus/minus eigenvector pairs are present,
  finite, and on matching grids.
- The stored EoE eigenvector shifts already include the Bartlett factor
  1.002158; the plotting pipeline does not apply it a second time.
- The EoE archive is marked legacy because its steering sets n_iterations=2.
  All five EoE sources in this run are fitted directly in MINUIT (:E:M:D);
  the remaining Gaussian sources use :N. Thus this setting is not itself
  evidence of unconverged EoE profiling. Final fit checks above pass.
- The raw EoE output reports NDF=1122 because it also counts five external
  nuisance parameters. The paper uses the common 1127 PDF-fit degrees of
  freedom; the comparison does not equate these two conventions.

## Plot convention and observations

`config.yaml` matches the existing BG Figure 3 convention: Q2 = 4 GeV2,
symmetric Pumplin bands from native xFitter grids, 100 logarithmically
spaced x values from 1e-4 to 0.9, and ratio limits 0.6 to 1.6. Blue is the
resummed Gaussian baseline, red is the resummed five-source EoE fit.
Each ratio and its band is divided by the baseline central PDF, without
propagating a second denominator uncertainty.

On the displayed grid, all three EoE central PDFs lie inside their
Gaussian bands, with maximum shifts of 0.60, 0.21 and 0.65 baseline
standard deviations for uv, dv and gluon. The low-x gluon band width is
nearly unchanged; valence intervals have modest changes which depend on x.
Full numerical summaries are in `results/pdf_summary.json`.

The BG comparison itself is left unchanged. Its existing paper figure was
checked against its comparison-workspace PDF and visually reviewed.
Its full archived EoE uncertainty-grid set is no longer available in the
reorganised fit folders, so it was not regenerated from a partial fallback.
The proposed paragraph retains qualitative observations supported by the
published BG figure, including its smaller low-x gluon compared with the
resummed configuration. Differences between those two configurations also
include heavy-flavour treatment and input settings, as the paper explains.

## Artifacts and reproduction

- `plots/pdf_comparison.pdf`: native three-page pipeline output for use
  with the paper's existing six-panel includegraphics arrangement.
- `preview/figure4_candidate.pdf` and `.png`: assembled six-panel preview.
- `preview/unified_pdf_paragraph.tex`: original paragraph shown for review.
- `preview/implemented_pdf_paragraph.tex`: revised paragraph installed
  after user approval and the requested changes to the text.
- `preview/figure4_caption.tex`: caption installed in the manuscript.
- `paper-before.sha256.json`: manuscript and installed figure hashes
  recorded before preparing this preview.
- `results/paper_unchanged.json`: historical verification that the preview
  stage did not change the paper, before the user approved installation.

From the repository root, after activating the LCG environment:

```bash
source /cvmfs/sft.cern.ch/lcg/views/LCG_106/x86_64-el9-gcc13-opt/setup.sh
export MPLCONFIGDIR=/tmp/eoe-fig4-mpl-cache
export PYTHONPATH="/nfs/scratch2/ecanoner/xfitter-eoe-runs/src${PYTHONPATH:+:$PYTHONPATH}"
scripts/plot-pdf-comparison runs/comparisons/smallx-gaussian-vs-5sources-pumplin-20260818
python runs/comparisons/smallx-gaussian-vs-5sources-pumplin-20260818/summarize.py
cd runs/comparisons/smallx-gaussian-vs-5sources-pumplin-20260818/preview
pdflatex -interaction=nonstopmode -halt-on-error figure4_candidate.tex
pdftoppm -r 200 -singlefile -png figure4_candidate.pdf figure4_candidate
```
