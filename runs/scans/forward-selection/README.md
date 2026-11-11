# Systematic-source ranking

[Repository](../../../README.md) · [Installation](../../../docs/installation.md) ·
[HERA study](../../../docs/hera-study.md) ·
[HERA examples](../../../docs/hera-scans.md#forward-selection) ·
[Paper reproduction](../../../docs/reproducing-paper.md)

`scan_type: systematic-ranking` compares a base fit with fits that activate
one additional systematic source at a time. It produces a ranking for one
specified base. To construct a forward-selection chain, choose a valid candidate
and prepare another configuration with that source added to the base.

## Configuration and inputs

Create a workspace under `runs/scans/` with a `config.yaml`. The path identifies
your study; the `scan_type` field selects this implementation.

| Field | Meaning |
| --- | --- |
| `scan_type` | `systematic-ranking` |
| `template` | Directory name under root `templates/` |
| `datafiles` | Dataset filenames copied into each generated fit |
| `systematics` | Candidate source entries: `name`, `type`, optional `range`, `epsilon`, `init` |
| `base_systematics` | Optional sources active in every fit; same entry format |
| `epsilon` | Default EoE strength when an entry does not provide `epsilon` |
| `n_iterations`, `enable_bartlett`, `q2_cut` | Options passed to the steering template |
| `doErrors` | Optional error method; Pumplin accepts `errdef` and `iterate` |
| `xfitter_tree`, `xfitter_commit` | Build directory and optional exact revision for workers |
| `request_memory` | Condor memory request |

The template supplies `steering.txt.j2`, `parameters.yaml.j2`,
`constants.yaml` and `unpolarised.wgt`. Source names and types must match the
selected dataset and xFitter setup. Ranges expand numbered names; candidates
already present in `base_systematics` are excluded. `init` supplies starting
values for E-type nuisances, not fixed shifts.

The current `scripts/run-scan` adapter resolves `datafiles` inside its fixed
HERA dataset directory; there is no CLI option or YAML field that changes that
root. The library's `run_scan` accepts an explicit `dataset_root`. See
[installation](../../../docs/installation.md) for this adapter boundary and the
scientific runtime. Generation requires templates and data, but does not read
a preceding round's fit output.

## Commands

These commands require `workspace` to be set to **your existing scan directory**
under `runs/scans/`. They are a command template, not a supplied study. For a
concrete selection and configuration, use the [HERA examples](../../../docs/hera-scans.md#forward-selection).
Run from the repository root after installation.

Preview without writing files:

```bash
python scripts/run-scan --dry-run "${workspace:?Set workspace to your scan directory}"
```

Generate inputs and batch files without submitting:

```bash
python scripts/run-scan --no-submit "${workspace:?Set workspace to your scan directory}"
```

Submit that generated batch:

```bash
bash "${workspace:?Set workspace to your scan directory}/runs/submit.sh"
```

After the fits finish, extract results and plot:

```bash
scripts/plot-scan "${workspace:?Set workspace to your scan directory}"
```

Generation writes the workspace's `runs/` tree; use a new workspace when
preserving previous inputs/results. Replotting saved fits needs only the last
command. Omitting both scan flags generates and submits in one operation.

## Outputs and interpretation

The runner creates `runs/nominal/` with only the base sources and
`runs/<source>/` for each remaining candidate. The base is Gaussian only when
no EoE sources are active. With *N* candidates after filtering, expect *N + 1*
entries in `runs/batch/fit_dirs.txt`.

| Output within the workspace | Contents |
| --- | --- |
| `runs/batch/batch.log` | Condor events after submission |
| `runs/<fit>/output/Results.txt`, `minuit.out.txt` | Fit statistic, nuisance information and minimizer output |
| `runs/<fit>/output/xfitter_provenance.txt` | Worker executable and library provenance |
| `results/chi2.csv` | Base and candidate statistics and convergence flags |
| `results/parameters.csv` | Parameter values and errors in wide format |
| `results/rankings.csv` | Candidates ordered by corrected improvement |
| `plots/chi2_ranking.pdf`, `plots/parameters.pdf` | Ranking and parameter diagnostics |

`dchi2_corrected` is the base's Bartlett-corrected minimum minus the candidate's
corrected minimum. Both endpoints use their own correction. The runner does
not choose a winner, enforce a stopping threshold or construct another round;
those are study decisions.

Compare extracted rows with the generated inventory. Missing or invalid outputs
can be omitted; non-converged candidates remain ranked with `non_converged`
set. Inspect `base_converged`, the worker provenance and final fit status before
accepting an improvement. A sorted CSV alone does not establish a valid winner.
