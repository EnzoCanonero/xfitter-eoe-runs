# Regional cross-section χ² tables

This reusable comparison bins fitted measurements in Q² and x and reports the
change in the data contribution to χ² between two fits. Both fit labels, the
region boundaries and the dataset filter are configurable. It can compare
compatible DIS fits over any covered kinematic range; it is not restricted to
a particular HERA setup or to low Q² and small x.

See [installation](../../../docs/installation.md),
[HERA study definitions](../../../docs/hera-study.md),
[HERA table example](../../../docs/hera-comparisons.md#regional-table) and
[paper reproduction](../../../docs/reproducing-paper.md).

## Workspace and configuration

Create `runs/comparisons/regions/<setup>/<comparison>/config.yaml`. The example
uses placeholder fit paths and illustrates custom bins:

```yaml
type: xsec-region-table
q2bins: [0, 25, 100, 10000]
xbins: [0, 0.01, 0.05, 0.5, 1.0]
dataset: ""
fits:
  - {label: "Reference", path: "../../../../fits/my-setup/reference"}
  - {label: "Alternative", path: "../../../../fits/my-setup/alternative"}
```

Exactly two fit entries are required. The first is the reference and the second
is the comparison. Their paths may be absolute or relative to the workspace,
and may point to a fit root or its `output/` directory. Each location must
contain `fittedresults.txt`.

| Key | Meaning |
| --- | --- |
| `q2bins` | Strictly increasing Q² **edges**, in GeV²; at least two |
| `xbins` | Strictly increasing x **edges**; at least two |
| `dataset` | Optional substring matched against dataset labels; empty or omitted selects all |
| `fits` | Exactly two entries with arbitrary `label` and `path` values |

With N Q² edges and M x edges, the table has (N−1) × (M−1) cells. Bins include
the lower edge and exclude the upper edge. Points outside the edge arrays are
reported and excluded. Explicit arrays make the scientific selection clear;
if omitted or empty, the implementation defaults to Q² edges
`[0, 10, 30, 100, 1000, 1e9]` and x edges `[0, 0.001, 0.01, 0.1, 1]`.
Unlike [cross-section plotting](../xsec/README.md), `q2bins` here means edges,
not a list of individual slices.

## Input constraints and statistic

The reader supports the standard DIS layout of xFitter's `fittedresults.txt`:
numbered dataset blocks followed by labels, with Q², x and the fitted pull in
columns 1, 2 and 11 respectively. Rows must have at least 13 columns. The
coordinate and pull columns cannot be changed by configuration, so this is
not a general table reader for arbitrary reaction observables.

After dataset filtering, the fits must contain the same number of rows in the
same order. The reader checks matching dataset labels and coordinates, using
absolute tolerances of 10⁻⁹ for Q² and 10⁻¹² for x. It does not reorder rows or
perform a join; it also does not compare every measurement column. Use fits of
the same measurements and a consistent pull convention.

For each cell:

```text
Δχ²_data = sum(pull_comparison² - pull_reference²)
```

A negative entry means the comparison has a smaller data-term χ² in that
region. The pull uses the prediction after systematic shifts. The calculation
excludes nuisance-parameter constraints, the prediction-dependent logarithmic
term and any global Bartlett correction. Its total is therefore not the change
in full or corrected fit χ². Read those quantities separately from the fit
outputs.

## Generate and inspect the table

Run from the repository root after supplying the configured inputs:

```bash
workspace=runs/comparisons/regions/my-setup/my-comparison
scripts/plot-xsec "$workspace"
```

The shared command dispatches on `type: xsec-region-table`. Its shell wrapper
initializes the configured xFitter/LCG environment through
[setup-env.sh](../../../scripts/setup-env.sh), so `.env` and the built-tree
checks apply. The table handler uses Python and the YAML reader; it does not
invoke ROOT, `xfitter-draw` or LaTeX. PyYAML supports the full YAML syntax.

The command prints a table and replaces:

| File | Content |
| --- | --- |
| `results/region_table.csv` | One row per cell, including empty cells; columns `q2_lo,q2_hi,x_lo,x_hi,npoints,dchi2`; Δχ² to four decimal places |
| `results/region_table.tex` | LaTeX `tabular` with values and counts, empty-cell dashes, row/column totals and a grand total; Δχ² to one decimal place |

The TeX file is a fragment without a caption or document wrapper. Its last
Q²/x labels are displayed as lower bounds even though the final configured
upper edges still apply. Choose upper edges covering the intended sample, or
state those limits in the caption. Q² units also belong in the caption.
No PDF is generated.

For a simple read-only summary of a generated CSV:

```bash
python3 - "$workspace/results/region_table.csv" <<'PY'
import csv
import sys

with open(sys.argv[1]) as stream:
    rows = list(csv.DictReader(stream))
print('cells:', len(rows))
print('points:', sum(int(row['npoints']) for row in rows))
print('summed Δχ²_data:', sum(float(row['dchi2']) for row in rows))
PY
```

Compare the cell count with the configured edges, the summed point count with
the selected measurements, and any excluded-point report with the intended
coverage. Small differences between summed CSV values and the console total
can arise from rounding. The [HERA example](../../../docs/hera-comparisons.md#regional-table)
gives a concrete numerical check for the supplied study.
