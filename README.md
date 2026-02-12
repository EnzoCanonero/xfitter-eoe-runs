# xfitter EoE Runs

Collaborative workspace for xFitter runs from scratch space.
Code/binaries stay in `~/PDF/xfitter-master`; this repo tracks fit configs and run scaffolding.

## Layout

```
xfitter-eoe-runs/
├── setup_env.sh
├── new_fit.sh
├── datafiles/                  # symlink -> ~/PDF/xfitter-master/datafiles
├── studies/                    # study notes/logbook (one file per study family)
└── fits/
    ├── hera/
    │   └── hera-baseline/
    │       ├── eoe/
    │       ├── nominal/
    │       └── eoe-no-bartlett/
    └── sandbox/                # local throwaway work (ignored except .gitkeep)
```

Each fit directory contains:
- `config/` editable fit config (`steering.txt`, `parameters.yaml`, plus shared symlinks)
- `condor/` batch scripts (`run_fit.sh`, `job.sub`, `logs/`)
- `datafiles/` symlink to shared data
- `output/` runtime products (ignored)

## Workflow (Git + collaboration)

- Use a branch-per-study strategy, e.g. `study/hera-baseline-eoe-v2`.
- Keep study rationale and decisions in `studies/<study>.md`.
- Keep fit variants under nested paths in `fits/`.
- Commit only configs/scripts/docs; `output/` and `condor/logs/` are ignored.

## Create a new fit

```bash
# New fit from default template
./new_fit.sh hera/hera-baseline/test-variant

# New fit from custom template
./new_fit.sh my-study/alt-template /path/to/template
```

`new_fit.sh` supports nested fit paths and creates an absolute `datafiles` symlink so any depth works.

## Run a fit

```bash
cd fits/hera/hera-baseline/eoe
condor_submit condor/job.sub
```

`condor/run_fit.sh` stages `config/*` into the fit root, runs `xfitter`, then removes staged symlinks.
