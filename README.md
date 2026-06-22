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

## Git workflow

- Branch per study, e.g. `study/hera-baseline-eoe-v2`.
- Study rationale in `studies/<study>.md`.
- Commit only configs/scripts/docs; `output/`, `condor/logs/`, and `*.dat` data files are gitignored.
