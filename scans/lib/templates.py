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
            **kwargs
        }

        rendered = template.render(context)
        if not rendered.endswith('\n'):
            rendered += '\n'
        return rendered

    def render_parameters(self, fit_dir: Path, do_errors: Optional[str] = None) -> str:
        template = self.env.get_template('parameters.yaml.j2')
        return template.render({'do_errors': do_errors})


def create_fit_structure(fit_dir: Path,
                         steering_content: str,
                         parameters_content: str,
                         datafiles: List[str],
                         template_dir: Path,
                         do_errors: Optional[str] = None):
    """Create a fit directory from a template folder.

    template_dir is a folder under scans/templates/ (e.g. hera-baseline/, giuli/)
    holding parameters.yaml.j2, constants.yaml and unpolarised.wgt. It is required —
    the study config selects it via its `template:` field (config.template_dir).
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

    repo_root = Path(__file__).parent.parent.parent
    datafiles_source = repo_root / "datafiles" / "hera" / "h1zeusCombined" / "inclusiveDis" / "1506.06042"
    for datafile in datafiles:
        src = datafiles_source / datafile
        if src.exists():
            shutil.copy2(src, config_dir / datafile)

    submit_script_path = fit_dir / "condor" / "submit.sh"
    submit_script_path.write_text(generate_submit_script(fit_dir))
    submit_script_path.chmod(0o755)


def generate_submit_script(fit_dir: Path) -> str:
    return r"""#!/bin/bash
# Generate condor scripts with correct absolute paths and submit.
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
FIT_DIR="$(cd "$DIR/.." && pwd)"

# Find setup_env.sh at the repo root
REPO_ROOT="$DIR"
while [ ! -f "$REPO_ROOT/setup_env.sh" ] && [ "$REPO_ROOT" != "/" ]; do
    REPO_ROOT="$(dirname "$REPO_ROOT")"
done
[ -f "$REPO_ROOT/setup_env.sh" ] || { echo "Cannot find setup_env.sh" >&2; exit 1; }

mkdir -p "$DIR/logs" "$FIT_DIR/output"

# ── Generate run_fit.sh ──────────────────────────────────────
cat > "$DIR/run_fit.sh" << EOF
#!/bin/bash
set -e
export HOME="\${HOME:-/tmp}"
source "$REPO_ROOT/setup_env.sh"

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


def _find_repo_root(start: Path) -> Path:
    """Walk up from `start` to the directory containing setup_env.sh."""
    repo_root = start.resolve()
    while repo_root != repo_root.parent:
        if (repo_root / "setup_env.sh").exists():
            return repo_root
        repo_root = repo_root.parent
    raise FileNotFoundError(f"setup_env.sh not found above {start}")


def generate_batch_submit(fits_dir: Path, fit_dirs: List[Path]) -> Path:
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
    repo_root = _find_repo_root(fits_dir)
    batch_dir = fits_dir / "batch"
    batch_dir.mkdir(parents=True, exist_ok=True)

    fit_dirs_file = batch_dir / "fit_dirs.txt"
    fit_dirs_file.write_text("\n".join(str(d) for d in fit_dirs) + "\n")

    run_fit = batch_dir / "run_fit.sh"
    run_fit.write_text(f"""\
#!/bin/bash
set -e
FIT_DIR="$1"
export HOME="${{HOME:-/tmp}}"
source "{repo_root}/setup_env.sh"

SHIM_DIR=$(mktemp -d)
trap "rm -rf $SHIM_DIR" EXIT
ln -s /cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc13-opt/lib/libopenblas.so \\
      "$SHIM_DIR/libflexiblas.so.3"
export LD_LIBRARY_PATH="$SHIM_DIR:$LD_LIBRARY_PATH"

cd "$FIT_DIR/config"
xfitter
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
request_memory      = 2GB
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
