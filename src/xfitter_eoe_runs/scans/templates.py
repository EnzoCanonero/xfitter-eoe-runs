"""
Jinja2 templating for steering files
Generates xFitter configuration files from templates
"""

from pathlib import Path
from typing import List, Tuple, Dict, Optional
from jinja2 import Environment, FileSystemLoader, Template


class TemplateManager:
    """Manage Jinja2 templates for steering files"""

    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def render_steering(self,
                        sources: List[Tuple[str, str, float]],
                        datafiles: List[str],
                        **kwargs) -> str:
        template = self.env.get_template('steering.txt.j2')

        context = {
            'sources': sources,
            'datafiles': datafiles,
            'chi2_settings_names': kwargs.get('chi2_settings_names',
                                              ['StatScale', 'UncorSysScale', 'CorSysScale',
                                               'UncorChi2Type', 'CorChi2Type']),
            'chi2_settings': kwargs.get('chi2_settings',
                                        ['Poisson', 'Linear', 'Linear', 'Diagonal', 'Hessian']),
            'chi2_extra_param': kwargs.get('chi2_extra_param', 'PoissonCorr'),
            'n_iterations': kwargs.get('n_iterations', 2),
            'enable_bartlett': kwargs.get('enable_bartlett', True),
            'q2_cut': kwargs.get('q2_cut', 3.5),
            **kwargs
        }

        rendered = template.render(context)
        if not rendered.endswith('\n'):
            rendered += '\n'
        return rendered

    def render_parameters(self, fit_dir: Path, do_errors: Optional[str] = None) -> str:
        template = self.env.get_template('parameters.yaml.j2')
        return template.render({'do_errors': do_errors})


def _xfitter_tree_export(xfitter_tree: Optional[str]) -> str:
    """`export XFITTER_TREE=...` line for a generated run script, or ''.

    setup-env.sh honours XFITTER_TREE to pick the build under $XFITTER_ROOT, but
    the condor job does not inherit the submitting shell's environment, so the
    export has to be written into the script itself. Without it a scan silently
    uses whatever .env defaults to -- which is how scans were run against the
    pre-Bartlett-fix build.
    """
    return f'export XFITTER_TREE={xfitter_tree}\n' if xfitter_tree else ''


def create_fit_structure(fit_dir: Path,
                         steering_content: str,
                         parameters_content: str,
                         datafiles: List[str],
                         template_dir: Path,
                         dataset_root: Path,
                         setup_env: Path,
                         do_errors: Optional[str] = None,
                         xfitter_tree: Optional[str] = None):
    """Create a fit directory from a template folder.

    template_dir is selected by the study config and contains parameters.yaml.j2,
    constants.yaml and unpolarised.wgt. dataset_root and setup_env are supplied
    by the command layer so this module has no repository-layout dependency.
    """
    import shutil

    fit_dir.mkdir(parents=True, exist_ok=True)
    config_dir = fit_dir / "config"
    config_dir.mkdir(exist_ok=True)
    (fit_dir / "condor").mkdir(exist_ok=True)
    (fit_dir / "output").mkdir(exist_ok=True)

    (config_dir / "steering.txt").write_text(steering_content)

    template_manager = TemplateManager(template_dir)
    parameters_content = template_manager.render_parameters(fit_dir, do_errors=do_errors)
    (config_dir / "parameters.yaml").write_text(parameters_content)

    shutil.copy(template_dir / "constants.yaml", config_dir / "constants.yaml")
    shutil.copy(template_dir / "unpolarised.wgt", config_dir / "unpolarised.wgt")

    for datafile in datafiles:
        src = dataset_root / datafile
        if src.exists():
            shutil.copy2(src, config_dir / datafile)

    submit_script_path = fit_dir / "condor" / "submit.sh"
    submit_script_path.write_text(
        generate_submit_script(fit_dir, setup_env, xfitter_tree)
    )
    submit_script_path.chmod(0o755)


def generate_submit_script(fit_dir: Path, setup_env: Path,
                           xfitter_tree: Optional[str] = None) -> str:
    setup_env = setup_env.resolve()
    setup_env_assignment = f'SETUP_ENV="{setup_env}"\n'
    return r"""#!/bin/bash
# Generate condor scripts with correct absolute paths and submit.
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
FIT_DIR="$(cd "$DIR/.." && pwd)"
""" + setup_env_assignment + r"""[ -f "$SETUP_ENV" ] || { echo "Cannot find $SETUP_ENV" >&2; exit 1; }

mkdir -p "$DIR/logs" "$FIT_DIR/output"

# ── Generate run_fit.sh ──────────────────────────────────────
cat > "$DIR/run_fit.sh" << EOF
#!/bin/bash
set -e
export HOME="\${HOME:-/tmp}"
""" + _xfitter_tree_export(xfitter_tree) + r"""source "$SETUP_ENV"

# Record exact executable/library provenance. The selected tree may contain
# local changes, so its name and Git commit alone are insufficient.
XFITTER_BIN=\$(command -v xfitter)
XFITTER_TREE_DIR=\$(cd "\$(dirname "\$XFITTER_BIN")/.." && pwd)
{
  echo "binary=\$XFITTER_BIN"
  echo "git_commit=\$(git -C "\$XFITTER_TREE_DIR" rev-parse HEAD 2>/dev/null || echo unavailable)"
  if [ -n "\$(git -C "\$XFITTER_TREE_DIR" status --porcelain --untracked-files=no 2>/dev/null)" ]; then
    echo "git_dirty=true"
  else
    echo "git_dirty=false"
  fi
  find "\$XFITTER_TREE_DIR/bin" "\$XFITTER_TREE_DIR/lib/xfitter" \
       -maxdepth 1 -type f -print0 2>/dev/null | sort -z | xargs -0 sha256sum
} > "$FIT_DIR/output/xfitter_provenance.txt"

# flexiblas shim (condor nodes miss libflexiblas, map to openblas)
SHIM_DIR=\$(mktemp -d)
trap "rm -rf \$SHIM_DIR" EXIT
ln -s /cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc13-opt/lib/libopenblas.so \
      "\$SHIM_DIR/libflexiblas.so.3"
export LD_LIBRARY_PATH="\$SHIM_DIR:\$LD_LIBRARY_PATH"

cd "$FIT_DIR/config"
xfitter
EOF
chmod +x "$DIR/run_fit.sh"

# ── Generate job.sub ─────────────────────────────────────────
cat > "$DIR/job.sub" << EOF
universe            = vanilla
executable          = $DIR/run_fit.sh
output              = $DIR/logs/output.log
error               = $DIR/logs/error.log
log                 = $DIR/logs/run.log
should_transfer_files = NO
initialdir          = $FIT_DIR/config
request_cpus        = 1
request_memory      = 2GB
queue 1
EOF

# ── Set OutputDirectory in parameters.yaml ───────────────────
sed -i "s|^OutputDirectory:.*|OutputDirectory: \"$FIT_DIR/output\"|" "$FIT_DIR/config/parameters.yaml"

# ── Submit ───────────────────────────────────────────────────
condor_submit "$DIR/job.sub"
"""


def generate_batch_submit(fits_dir: Path, fit_dirs: List[Path],
                          setup_env: Path,
                          xfitter_tree: Optional[str] = None,
                          request_memory: str = "2GB") -> Path:
    """
    Generate a single-cluster Condor batch submission for a scan.

    Produces:
      runs/batch/fit_dirs.txt      — one absolute fit-dir path per line
      runs/batch/run_fit.sh        — shared executable; receives fit_dir as $1
      runs/batch/condor_batch.sub  — queue fitdir from fit_dirs.txt
      runs/submit.sh               — driver: mkdir logs/output, patch OutputDirectory, condor_submit

    Returns:
        Path to runs/submit.sh
    """
    setup_env = setup_env.resolve()
    tree_export = _xfitter_tree_export(xfitter_tree)
    smallx_guard = ""
    smallx_provenance = ""
    if xfitter_tree == "xfitter-bartlett-apfel306-hell3":
        smallx_guard = '''\
EXPECTED_TREE="$XFITTER_ROOT/$XFITTER_TREE"
if [ "$XFITTER_TREE_DIR" != "$EXPECTED_TREE" ]; then
    echo "Unexpected xFitter tree: $XFITTER_TREE_DIR" >&2
    exit 2
fi

APFEL_PREFIX="$XFITTER_ROOT/deps/apfel"
APFEL_MODULE="$XFITTER_TREE_DIR/lib/xfitter/libevolutionAPFEL.so"
APFEL_LIB=$(ldd "$APFEL_MODULE" | awk '$1 ~ /^libAPFEL/ {print $3; exit}')
case "$APFEL_LIB" in
    "$APFEL_PREFIX"/lib/*) ;;
    *)
        echo "Unexpected APFEL library: ${APFEL_LIB:-not resolved}" >&2
        exit 3
        ;;
esac
'''
        smallx_provenance = '''\
  echo "apfel_library=$APFEL_LIB"
  echo "apfel_version=$("$APFEL_PREFIX/bin/apfel-config" --version)"
  sha256sum "$APFEL_LIB"
  echo "[APFEL module linkage]"
  ldd "$APFEL_MODULE"
'''
    batch_dir = fits_dir / "batch"
    batch_dir.mkdir(parents=True, exist_ok=True)

    fit_dirs_file = batch_dir / "fit_dirs.txt"
    fit_dirs_file.write_text("\n".join(str(d) for d in fit_dirs) + "\n")

    run_fit = batch_dir / "run_fit.sh"
    run_fit.write_text(f"""\
#!/bin/bash
set -eo pipefail
FIT_DIR="$1"
export HOME="${{HOME:-/tmp}}"
{tree_export}source "{setup_env}"

# Record exact executable/library provenance. The selected tree may be dirty.
XFITTER_BIN=$(command -v xfitter)
XFITTER_TREE_DIR=$(cd "$(dirname "$XFITTER_BIN")/.." && pwd)
{smallx_guard}
{{
  echo "binary=$XFITTER_BIN"
  echo "git_commit=$(git -C "$XFITTER_TREE_DIR" rev-parse HEAD 2>/dev/null || echo unavailable)"
  if [ -n "$(git -C "$XFITTER_TREE_DIR" status --porcelain --untracked-files=no 2>/dev/null)" ]; then
    echo "git_dirty=true"
  else
    echo "git_dirty=false"
  fi
  find "$XFITTER_TREE_DIR/bin" "$XFITTER_TREE_DIR/lib/xfitter" \
       -maxdepth 1 -type f -print0 2>/dev/null | sort -z | xargs -0 sha256sum
  if [ -f "$XFITTER_TREE_DIR/lib/libxfitter.so" ]; then
    sha256sum "$XFITTER_TREE_DIR/lib/libxfitter.so"
  fi
{smallx_provenance}\
}} > "$FIT_DIR/output/xfitter_provenance.txt"

SHIM_DIR=$(mktemp -d)
trap "rm -rf $SHIM_DIR" EXIT
ln -s /cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc13-opt/lib/libopenblas.so \\
      "$SHIM_DIR/libflexiblas.so.3"
export LD_LIBRARY_PATH="$SHIM_DIR:$LD_LIBRARY_PATH"

cd "$FIT_DIR/config"
RUN_LOG="$FIT_DIR/output/xfitter_run.log"
xfitter 2>&1 | tee "$RUN_LOG"

# HELL and loader failures do not always propagate a non-zero process status.
if grep -Eqi 'HELLx: Error|Fortran runtime error|symbol lookup error|error while loading shared libraries' "$RUN_LOG"; then
    echo "Fatal runtime signature found in $RUN_LOG" >&2
    exit 4
fi

if [ ! -s "$FIT_DIR/output/Results.txt" ]; then
    echo "Missing or empty Results.txt for $FIT_DIR" >&2
    exit 5
fi

if [ ! -s "$FIT_DIR/output/minuit.out.txt" ]; then
    echo "Missing or empty minuit.out.txt for $FIT_DIR" >&2
    exit 6
fi
""")
    run_fit.chmod(0o755)

    sub_file = batch_dir / "condor_batch.sub"
    sub_file.write_text(f"""\
universe            = vanilla
executable          = {batch_dir}/run_fit.sh
arguments           = $(fitdir)
output              = $(fitdir)/condor/logs/output.log
error               = $(fitdir)/condor/logs/error.log
log                 = {batch_dir}/batch.log
should_transfer_files = NO
initialdir          = $(fitdir)/config
request_cpus        = 1
request_memory      = {request_memory}
queue fitdir from {fit_dirs_file}
""")

    submit_script = fits_dir / "submit.sh"
    submit_script.write_text(f"""\
#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Preparing {len(fit_dirs)} fit directories..."
while IFS= read -r fit_dir; do
    mkdir -p "$fit_dir/condor/logs" "$fit_dir/output"
    sed -i "s|^OutputDirectory:.*|OutputDirectory: \\"$fit_dir/output\\"|" \\
        "$fit_dir/config/parameters.yaml"
done < "{fit_dirs_file}"

echo "Submitting batch ({len(fit_dirs)} jobs)..."
condor_submit "{sub_file}"
""")
    submit_script.chmod(0o755)

    return submit_script
