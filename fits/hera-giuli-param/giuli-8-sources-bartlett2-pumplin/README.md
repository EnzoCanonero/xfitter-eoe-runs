# Final Giuli epsilon=0.6 greedy fit

This standalone fit is the publication-output counterpart of the final
Bonvini--Giuli greedy-selection endpoint in
`scans/studies/syst-ranking/giuli-param/9th-1053-1062-1111-1114-1144-tb21-1064-1113/runs/nominal`.

It fits the eight selected sources externally at `epsilon=0.6`, uses the
corrected Bartlett implementation from `xfitter-bartlett-fixes`, and computes
68.3% PDF uncertainties with Pumplin (`ERRDEF 0.5`, `ITERATE 10`).  The fit is
prepared for submission with `condor/submit.sh`.  After a successful fit the
wrapper corrects the LHAPDF member metadata and records the executable, Git
state, and library hashes used.  Preparing this directory does not submit the
job.
