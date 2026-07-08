# xFitter EoE Runs

Collaborative workspace for xFitter runs from scratch space.
Code/binaries stay in `~/PDF/xfitter-master`; this repo tracks fit configs and run scaffolding.

## Setup

1. Clone the repo to any NFS-accessible location.
2. Edit `.env` and set `XFITTER_ROOT` to your xFitter install path.
   The path must be accessible from Condor worker nodes (e.g. on NFS).

## Layout

```
xfitter-eoe-runs/
├── setup_env.sh                # environment for xfitter (CVMFS + NFS deps)
├── datafiles/                  # canonical source data (copied into fits by scripts)
├── studies/                    # study notes/logbook (one file per study family)
├── fits/                       # individual fits (manual)
│   ├── new_fit.sh
│   ├── hera/
│   │   └── hera-baseline/
│   │       ├── eoe/
│   │       ├── nominal/
│   │       └── eoe-no-bartlett/
│   ├── compare/                # PDF-comparison tool (overlay fits' PDFs)
│   │   ├── bin/                #   plot
│   │   ├── lib/                #   Python framework
│   │   └── studies/            #   comparison studies (config.yaml)
│   └── sandbox/                # throwaway work (gitignored)
└── scans/                      # systematic scans (automated)
    ├── bin/                    # run-scan, plot
    ├── lib/                    # Python framework
    ├── templates/              # named template folders (one per setup)
    │   ├── hera-baseline/      #   14-param HERAPDF: steering + parameters + constants + weights
    │   └── giuli-param/        #   18-param Giuli parametrization (arXiv:1902.11125)
    └── studies/                # scan studies
```

### Templates

Each folder under `scans/templates/<name>/` is a self-contained xFitter setup:
`steering.txt.j2`, `parameters.yaml.j2`, `constants.yaml`, `unpolarised.wgt`.
Every study `config.yaml` **must** select one by name via a required `template:` field
(e.g. `template: hera-baseline` or `template: giuli-param`); it is resolved against
`scans/templates/`, so studies can be moved without breaking. To add a setup, drop a
new folder under `scans/templates/` and reference it by name.

## Fits

Each fit directory under `fits/` contains:
- `config/` — `steering.txt`, `parameters.yaml`, `constants.yaml`, `unpolarised.wgt`, and data files (`*.dat`)
- `condor/` — `submit.sh` (generates `run_fit.sh` + `job.sub` and submits)
- `output/` — xFitter output (gitignored)

xFitter runs from `config/` — all files it needs are there. `run_fit.sh` sources
`setup_env.sh` and adds the flexiblas shim needed on condor worker nodes.

### Create a new fit

```bash
cd fits/

# From default template (eoe)
./new_fit.sh hera/my-study/variant-a

# Clone from another existing fit
./new_fit.sh hera/my-study/variant-b hera/hera-baseline/nominal/config
```

`new_fit.sh` creates the full directory structure, copies data files into `config/`,
and generates condor scripts. `OutputDirectory` in `parameters.yaml` is set
automatically at runtime by `run_fit.sh`.

### Run a fit

```bash
fits/hera/hera-baseline/eoe/condor/submit.sh
```

## Scans

Automated framework for running systematic PDF fitting scans on Condor.

### Scan types

**Lambda-scan** — tests different global epsilon scaling factors (λ):
- Config: `lambda_min`, `lambda_max`, `lambda_step`, `base_epsilon`, `sources`, `datafiles`
- Output: chi2-vs-lambda plots, parameter heatmaps, convergence charts

**Systematic-ranking** — tests each systematic source individually:
- Config: `epsilon`, `systematics`, `datafiles`
- Output: rankings by goodness-of-fit contribution

**Likelihood-scan** — profile Δχ² scans around a reference fit (1D and/or 2D):
- Config: `reference_fit`, `systematics`, `datafiles`, `scan_defaults`, and any of
  `scan_params_1d` / `scan_systematics_1d` (1D) and `scan_params_2d` (2D). A study may
  contain 1D and 2D scans simultaneously.
- **1D**: each parameter fixed on a grid (`±n_sigma`, `npoints`), the rest profiled →
  `profiles_1d.pdf` (Δχ² vs parameter).
- **2D**: `scan_params_2d: [{pair: [X, Y]}, ...]` jointly fixes a pair on an
  `npoints_2d × npoints_2d` grid (axes `±n_sigma_2d`), the rest profiled. Contours are
  drawn at `sigma_levels` (default `[1,2,3]`) using **2-parameter joint** Δχ² levels
  (1σ=2.30, 2σ=6.18, 3σ=11.83) → `contours_2d.pdf`. Each axis may be a PDF parameter or
  an E-type systematic (inferred from `systematics`).

**Pumplin-stability** — Pumplin uncertainty stability over a `lambda × errdef × iterate` grid:
- Config: `eps` (base; source eps = `eps * lambda`), `lambda` (vector; a Gaussian
  fit with no `&Systematics` source is always added as `lambda_0.0`), `errdef` and
  `iterate` (Pumplin `SET ERRDEF` / `ITERATE` grids set per fit), `errdef_ref`
  (normalization, default 0.5), `systematics` (each with `type: E` or `N`), `datafiles`.
- Run dirs: `runs/lambda_<v>/errdef<X>p<Y>_iter<NN>/`.
- Output: per-parameter pages with **one panel per lambda** (≤4 panels/page, paginates
  beyond 4) — `pumplin_iteration_convergence.pdf` (interval vs ITERATE, line per ERRDEF)
  and `pumplin_errdef_invariance.pdf` (interval vs ERRDEF, line per ITERATE).

### Create and run a scan

```bash
cd scans/studies/
mkdir my-scan && cd my-scan

# Create config.yaml (see examples in existing studies)
cat > config.yaml << 'EOF'
scan_type: lambda-scan
template: hera-baseline       # required: a folder under scans/templates/
lambda_min: 0.0
lambda_max: 1.2
lambda_step: 0.1
base_epsilon: 0.5
datafiles:
  - HERA1+2_NCep_920-thexp.dat
  - HERA1+2_CCep-thexp.dat
sources:
  - {name: sysHZComb1042, type: N}
  - {name: proc_tb21, type: E}
EOF

# Create symlinks to commands
ln -s ../../bin/run-scan .
ln -s ../../bin/plot .

# Preview, then generate and submit
./run-scan --dry-run
./run-scan

# After fits complete, extract results and plot
./plot
```

Each study is self-contained: `config.yaml`, `runs/`, `results/`, `plots/`.

## Comparing fits (PDF plots)

`fits/compare/` overlays the parton distributions of an arbitrary number of **individual
fits** into one multi-page PDF (one page per observable), with a 2-panel layout: central
distributions + uncertainty band on the left, ratio-to-reference on the right. Each fit is
read from its own LHAPDF set at `<fit>/output/<set>` (default set `proton`).

It is config-driven, mirroring the scans UX (`cd <study> && plot`).

### Create and run a comparison

```bash
cd fits/compare/studies/
mkdir my-comparison && cd my-comparison

cat > config.yaml << 'EOF'
type: pdf-comparison
Q2: 10.0                      # observables evaluated at Q = sqrt(Q2) [GeV]
x_min: 1.0e-4
x_max: 0.9
observables: [uv, dv, gluon, sea]
error_type: asymmetric        # symmetric | asymmetric (used only when a set carries errors)
ratio_reference: 0            # ratio-panel denominator: fit index or label
fits:
  - {label: "Q2 > 2.0", path: ../../../hera/Q2cut/q2cut-2.0}
  - {label: "Q2 > 5.0", path: ../../../hera/Q2cut/q2cut-5.0}
  # An installed LHAPDF set can be overlaid instead of a fit dir:
  # - {label: "HERAPDF2.0 NNLO", lhapdf_set: HERAPDF20_NNLO_EIG}
EOF

ln -s ../../bin/plot .
./plot                        # writes plots/pdf_comparison.pdf
```

Each fit entry uses either `path` (a local fit dir, relative to the study) or
`lhapdf_set` (an installed set); optional `set`, `color`, `linestyle`, `label`.
Uncertainty bands are **auto-detected**: a set with `1+2N` members gets a Hessian band
(via `PDFSet.uncertainty`, honouring its `ErrorType`); a single-member set is drawn as a
central line only. Comparisons may freely mix the two.

## Git workflow

- Branch per study, e.g. `study/hera-baseline-eoe-v2`.
- Study rationale in `studies/<study>.md`.
- Commit only configs/scripts/docs; `output/`, `condor/logs/`, and `*.dat` data files are gitignored.
