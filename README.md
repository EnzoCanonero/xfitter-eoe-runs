# xFitter errors-on-errors studies

Tools for configuring and running xFitter errors-on-errors (EoE) studies,
extracting fit results, and comparing parton distributions and cross sections.
Study definitions specify the fit inputs and uncertainty treatment; comparison
definitions select the curves, scales, kinematic ranges and presentation.

[Installation](docs/installation.md) · [Workflow guides](runs/README.md) ·
[HERA application](docs/hera-study.md)

## What you can do

- Prepare fit workspaces from xFitter configurations and submit them to HTCondor.
- Study source selection, the size of errors on errors, likelihood profiles,
  and the stability of uncertainty calculations.
- Compare PDF central values and bands at a chosen Q² and x range.
- Select DIS datasets and Q² slices for cross-section overlays.

The repository includes the tools and a configured
[HERA application](docs/hera-study.md). Its parametrisations, source selections
and low-Q² plots are study choices. The comparison commands accept other
compatible inputs and kinematic selections.

Fit outputs and generated figures are local products and are **not included in
a clone**. Comparisons read completed fits; they do not rerun them.

## Start here

Follow [installation](docs/installation.md) to clone the repository and prepare
Python. From the repository root, in that environment:

```bash
python -m pip install .
python scripts/run-scan --help
```

This shows the scan command's options without creating files or submitting jobs.
Choose a workflow below to prepare a study. For a runnable example, use the
[supplied HERA scan preview](docs/hera-study.md#preview-the-supplied-example).
Fit execution additionally requires the
[scientific runtime](docs/installation.md#scientific-runtime).

All command examples in the guides run from the repository root. Use
`python scripts/run-scan` so the scan command uses your selected Python
environment. Preview, file generation, and job submission are separate steps.

## Choose a workflow

| Scientific question or task | Guide |
| --- | --- |
| How do I prepare and run a fit? | [Fit workspaces](runs/fits/README.md) |
| Which systematic sources benefit from an EoE treatment? | [Forward selection](runs/scans/forward-selection/README.md) |
| How do results depend on ε or a common scaling factor λ? | [EoE scans](runs/scans/eoe-scan/README.md) |
| What is the shape of the profiled χ²? | [Likelihood profiles](runs/scans/likelihood/README.md) |
| How stable are Pumplin uncertainty calculations? | [Pumplin stability](runs/scans/pumplin-stability/README.md) |
| How do PDF central values and bands change? | [PDF comparisons](runs/comparisons/pdf/README.md) |
| How do different fits describe selected DIS cross sections? | [Cross-section comparisons](runs/comparisons/xsec/README.md) |

Each guide explains the supported configuration, input format, commands and
output files. The [workspace index](runs/README.md) describes where new studies
belong. HERA-specific notation, configurations and manuscript presentation live
in the [application documentation](docs/hera-study.md).

## How the repository works

```text
Configurations + datasets → xFitter jobs → fit outputs → plots and tables
```

| Location | Contents |
| --- | --- |
| `runs/` | Study definitions and local generated results |
| `scripts/` | Commands for preparing, executing, and plotting studies |
| `src/xfitter_eoe_runs/` | Python implementation |
| `templates/` | xFitter inputs used to generate scan jobs |
| `datasets/` | Input data tables; the bundled collection is HERA inclusive DIS |
| `docs/` | Installation and application-specific documentation |
| `tests/` | Software tests |

Configurations and launchers are versioned. Generated `output/`, scan `runs/`,
`results/`, `plots/`, and runtime logs remain local. Dependencies between studies
are explicit in their configurations; a comparison consumes fit results rather
than rerunning the fits.

## Requirements and development

Python 3.9 or newer is sufficient for configuration previews and the software
tests. `pip` installs the Python dependencies. Fit execution additionally needs
the configured xFitter build and scientific libraries, a shared filesystem, and
HTCondor. The supplied workers use CERN LCG/CVMFS. PDF plotting needs LHAPDF;
cross-section plotting needs `xfitter-draw` and ROOT. See
[installation](docs/installation.md) for the environment required by each task.

For development and software validation:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

Scan configurations select their dataset directory and the parameters shown
in optional λ comparisons and Pumplin diagnostics. The
[installation](docs/installation.md) and workflow guides describe these fields
and the input formats required by each workflow.

These tests check the software and workspace conventions. Validate fit quality
and input compatibility for each scientific application. Commit source code,
configurations, and documentation; keep generated results outside Git.

## License

The project's code and documentation are available under the [MIT License](LICENSE).
External scientific software and datasets retain their respective terms.

I designed these tools for general use, but have applied them only to HERA so
far. Applications to other datasets may require adaptations. If you are
interested, please open an issue or discussion. I am happy to collaborate and
help adapt the tools, and to welcome active contributors as project
collaborators.
