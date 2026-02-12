# xfitter EoE Runs

Workspace for running xfitter fits with errors-on-errors from scratch space.
Source code and binaries remain in `~/PDF/xfitter-master`.

## Structure

```
xfitter-eoe-runs/
├── setup_env.sh      # sets PATH/LD_LIBRARY_PATH for xfitter
├── new_fit.sh        # creates a new fit directory
├── datafiles/        # symlink -> ~/PDF/xfitter-master/datafiles
└── fits/
    └── <fit-name>/
        ├── config/           # steering.txt, parameters.yaml, etc.
        ├── condor/           # run_fit.sh, job.sub, logs/
        ├── datafiles/        # symlink
        └── output/           # Results.txt, pdfs, etc. (created at runtime)
```

## Usage

```bash
# Create a new fit (defaults to EoE example template):
./new_fit.sh my-fit

# Or from a different template:
./new_fit.sh my-fit /path/to/template/dir

# Edit the configuration:
vim fits/my-fit/config/steering.txt
vim fits/my-fit/config/parameters.yaml

# Submit to condor:
cd fits/my-fit
condor_submit condor/job.sub

# Check results:
condor_q
cat fits/my-fit/output/Results.txt
```

## How it works

xfitter reads config files from its working directory. At runtime, `condor/run_fit.sh`
temporarily symlinks everything from `config/` into the fit root, runs xfitter, then
cleans up the symlinks. This keeps the fit directory tidy: only `config/`, `condor/`,
`datafiles/`, and `output/` persist.
