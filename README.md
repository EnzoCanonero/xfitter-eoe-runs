# xFitter EoE Runs

Collaborative workspace for xFitter runs from scratch space.
Code/binaries stay in `~/PDF/xfitter-master`; this repo tracks fit configs and run scaffolding.

## Layout

```
xfitter-eoe-runs/
├── setup_env.sh                # environment for xfitter (CVMFS + NFS deps)
├── datafiles/                  # symlink -> ~/PDF/xfitter-master/datafiles
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
    ├── templates/              # Jinja2 templates for xFitter config
    └── studies/                # scan studies
```

## Fits

Each fit directory under `fits/` contains:
- `config/` — `steering.txt`, `parameters.yaml`, `constants.yaml`, `unpolarised.wgt`, and data files (`*.dat`)
- `condor/` — `run_fit.sh`, `job.sub`, `logs/`
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
sets `OutputDirectory` in `parameters.yaml`, and generates condor scripts.

### Run a fit

```bash
condor_submit fits/hera/hera-baseline/eoe/condor/job.sub
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

### Create and run a scan

```bash
cd scans/studies/
mkdir my-scan && cd my-scan

# Create config.yaml (see examples in existing studies)
cat > config.yaml << 'EOF'
scan_type: lambda-scan
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
