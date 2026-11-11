# Cross-section comparisons

This tool overlays fitted cross-section predictions and uncertainty bands from
one or more fits with the measured data, using ROOT's native `xfitter-draw`
renderer. Dataset selection, Q² slices, x display ranges and labels are
configurable; the tool is not restricted to low-Q² or small-x panels.
It reads existing fit outputs without executing a fit.

See [installation](../../../docs/installation.md),
[HERA study definitions](../../../docs/hera-study.md),
[HERA comparison examples](../../../docs/hera-comparisons.md) and
[paper reproduction](../../../docs/reproducing-paper.md).

## Input format and workspace

Create a workspace under `runs/comparisons/xsec/<setup>/<comparison>/` with a
`config.yaml`. Each fit needs `fittedresults.txt` in its configured path or in
that path's `output/` subdirectory. Paths are relative to the comparison
workspace, or absolute. Labels can describe any fit or method.

The selection layer expects xFitter's DIS-style `fittedresults.txt`: numbered
dataset blocks, dataset labels, `Plot` metadata and numeric rows whose first
columns are Q² and x. It also reads the final plot index and the standard
`therr+`/`therr-` columns. This is not an arbitrary CSV reader or a configurable
coordinate adapter for other reaction formats. Compare outputs for compatible
measurements and kinematics.

Theory uncertainty bands require nonzero `therr+`/`therr-` values. Optional
`Results.txt`, `minuit.out.txt`, `parsout_0` and `parsout_1` files supply the
renderer's fit-summary pages. Those pages refer to the full fits even when only
some data panels are selected.

## Configuration and selection

This example uses placeholder paths and dataset labels; choose values present
in your inputs:

```yaml
type: xsec-comparison
panels:
  - {dataset: "Sample A", q2: 25.0}
  - {dataset: "Sample B", q2: 100.0}
fits:
  - {label: "Reference", path: "../../../../fits/my-setup/reference"}
  - {label: "Alternative", path: "../../../../fits/my-setup/alternative"}
therr: true
plots_per_page: 1
show_setup_annotation: false
```

There are two selection modes:

| Configuration | Selection |
| --- | --- |
| Nonempty `panels` list | Explicit dataset-substring/Q² pairs; takes precedence over `dataset` and `q2bins` |
| `dataset` and `q2bins` | A dataset-label substring and a list of Q² values; omitted or empty values select all matching datasets or all Q² values |

For example, `dataset: "Sample A"` and `q2bins: [25, 100, 1000]` selects those
three slices wherever present. Here `q2bins` means **slice values**. Matching
uses a Q² absolute tolerance of 10⁻⁶. Dataset substrings can match multiple blocks.
An empty selection fails. Output order follows the source dataset/plot order;
`panels` selects slices rather than defining an arbitrary page ordering.

The script stages selected rows in `.xfdraw-staging/`, normalizes plot indices
and Q² titles, and retains the source measurements, predictions and uncertainty
values. Successful completion removes staging. All-Q² selection is available;
the original fit cuts still determine which points exist in the inputs.

## Rendering options

| Key | Behavior |
| --- | --- |
| `therr`, `shifts`, `uncorr_ticks`, `logo`, `upband` | Element toggles, each defaulting to `true` |
| `plots_per_page` | Panels per native page; omitted means the renderer's default |
| `xrange` | Renderer x-axis display range, such as `"0.001:0.5"`; does not filter input rows |
| `ratiorange` | Ratio-axis display range, such as `"0.9:1.1"` |
| `ratio_to_theory` | Default `false`: ratio to data; `true`: use theory as denominator |
| `filledbands`, `transparentbands` | Band-style toggles, default `false` |
| `show_setup_annotation` | Display a shared annotation derived from optional fit `setup`/`treatment` metadata; default `true` |
| `extra_options` | List of additional native `xfitter-draw` arguments |
| `xfitter_tree` | Built tree containing `bin/xfitter-draw`, absolute or relative to `XFITTER_ROOT` |

When `ratio_to_theory` is enabled, the first fit supplies the reference name
passed to `--theory`; an explicit `--theory` in `extra_options` overrides that
annotation. It does not select a different numerical denominator. See the
[HERA example](../../../docs/hera-comparisons.md#cross-section-panels)
for one concrete choice of labels and panels.

## Environment, command and outputs

The wrapper always sources [setup-env.sh](../../../scripts/setup-env.sh).
Configure `.env` and the selected xFitter/LCG runtime before use. The renderer
requires `xfitter-draw`, ROOT, Ghostscript (`gs`, `ps2pdf`) and `pdflatex` for
summary pages. Make PyYAML available for the full configuration syntax.
These external dependencies are not installed by the Python package.

The renderer resolves its tree from config, then `XFITTER_TREE`, then the
configured default `merge-master/xfitter-master`. Environment initialization
uses `.env` or exported build settings: keep these consistent with a config's
`xfitter_tree`, and set `XFITTER_COMMIT` when a study requires a pinned build.
The config itself does not enforce a commit pin.

Run from the repository root after creating the workspace and supplying inputs:

```bash
workspace=runs/comparisons/xsec/my-setup/my-comparison
scripts/plot-xsec "$workspace"
```

The command writes or replaces `plots/xsec_comparison.pdf`, and copies
`plots/chi2.tex` and `plots/par.tex` when produced. Native summary pages may
follow the selected data panels. Their presence and the number of selected
slices determine the total page count; there is no fixed two-panel requirement.

With Poppler installed, use `pdfinfo "$workspace/plots/xsec_comparison.pdf"`
and inspect the selected dataset labels, Q² values and units, curve labels,
bands and ratio denominator. The console reports the selected point count for
each fit. Use original fit results for numerical fit-quality checks rather than
inferring them from selected data panels.
