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
        """
        Initialize template manager

        Args:
            template_dir: Path to directory containing templates (scans/templates/)
        """
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
        """
        Render steering.txt from template

        Args:
            sources: List of (source_name, source_type, epsilon) tuples
            datafiles: List of datafile paths
            kwargs: Additional template variables (chi2settings, n_iterations, etc.)

        Returns:
            Rendered steering file content
        """
        template = self.env.get_template('steering.txt.j2')

        # Pass sources as tuples directly (template expects: for name, type, eps in sources)
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
        # Ensure file ends with newline (required for Fortran namelist parsing)
        if not rendered.endswith('\n'):
            rendered += '\n'
        return rendered

    def render_parameters(self, fit_dir: Path, do_errors: Optional[str] = None) -> str:
        """
        Render parameters.yaml from template

        Args:
            fit_dir: Absolute path to fit directory (for OutputDirectory)
            do_errors: Optional doErrors multiline string for MINUIT section

        Returns:
            Rendered parameters file content
        """
        template = self.env.get_template('parameters.yaml.j2')

        context = {
            'fit_dir': str(fit_dir.resolve()),
            'do_errors': do_errors,
        }

        return template.render(context)


def create_fit_structure(fit_dir: Path,
                         steering_content: str,
                         parameters_content: str,
                         datafiles: List[str],
                         template_dir: Optional[Path] = None,
                         do_errors: Optional[str] = None):
    """
    Create xFitter fit directory structure

    Args:
        fit_dir: Path where fit directory should be created
        steering_content: Rendered steering.txt content
        parameters_content: Rendered parameters.yaml content (NOT USED - copied from template)
        datafiles: List of datafile paths
        template_dir: Optional template directory to copy other files from
    """
    # Create directory structure
    fit_dir.mkdir(parents=True, exist_ok=True)
    config_dir = fit_dir / "config"
    config_dir.mkdir(exist_ok=True)
    condor_dir = fit_dir / "condor"
    condor_dir.mkdir(exist_ok=True)
    output_dir = fit_dir / "output"
    output_dir.mkdir(exist_ok=True)

    # Find template directory (scans/templates/)
    if template_dir is None:
        # Default to scans/templates/
        scans_dir = Path(__file__).parent.parent
        template_dir = scans_dir / "templates"

    # Write steering file (templated)
    (config_dir / "steering.txt").write_text(steering_content)

    # Render parameters.yaml with fit_dir for OutputDirectory
    import shutil
    template_manager = TemplateManager(template_dir)
    parameters_content = template_manager.render_parameters(fit_dir, do_errors=do_errors)
    (config_dir / "parameters.yaml").write_text(parameters_content)

    # Copy constants.yaml from template (required by xFitter)
    shutil.copy(template_dir / "constants.yaml", config_dir / "constants.yaml")

    # Copy unpolarised.wgt from template (required by xFitter)
    shutil.copy(template_dir / "unpolarised.wgt", config_dir / "unpolarised.wgt")

    # Copy datafiles to config directory (for Condor file transfer)
    # Condor daemon doesn't have NFS access, so files must be local
    repo_root = Path(__file__).parent.parent.parent
    datafiles_source = repo_root / "datafiles" / "hera" / "h1zeusCombined" / "inclusiveDis" / "1506.06042"
    for datafile in datafiles:
        src = datafiles_source / datafile
        dst = config_dir / datafile
        if src.exists():
            shutil.copy2(src, dst)

    # Generate Condor submission script
    condor_script = generate_condor_script(fit_dir)
    (condor_dir / "job.sub").write_text(condor_script)

    # Generate run script
    run_script = generate_run_script(fit_dir)
    run_script_path = condor_dir / "run_fit.sh"
    run_script_path.write_text(run_script)
    run_script_path.chmod(0o755)


def generate_condor_script(fit_dir: Path) -> str:
    """
    Generate Condor submission script

    Args:
        fit_dir: Absolute path to fit directory

    Returns:
        Condor submit file content
    """
    fit_dir = fit_dir.resolve()  # Ensure absolute path
    condor_dir = fit_dir / "condor"

    # HERA datafiles to transfer (copied to config directory during fit generation)
    config_dir = fit_dir / "config"

    # Use relative paths from condor directory to config directory
    datafile_names = [
        "HERA1+2_NCep_920-thexp.dat",
        "HERA1+2_NCep_820-thexp.dat",
        "HERA1+2_NCep_575-thexp.dat",
        "HERA1+2_NCep_460-thexp.dat",
        "HERA1+2_NCem-thexp.dat",
        "HERA1+2_CCep-thexp.dat",
        "HERA1+2_CCem-thexp.dat"
    ]
    # Files are in ../config/ relative to condor/
    transfer_files = ", ".join([f"../config/{df}" for df in datafile_names])

    return f"""# Condor submission file for {fit_dir.name}
executable = {condor_dir / "run_fit.sh"}
output = {condor_dir / "job.out"}
error = {condor_dir / "job.err"}
log = {condor_dir / "job.log"}

# Run from config directory so transferred files are placed there
initialdir = {config_dir}

# File transfer (datafiles need to be transferred to worker nodes)
should_transfer_files = YES
when_to_transfer_output = ON_EXIT
transfer_input_files = {transfer_files}

# Requirements
request_cpus = 1
request_memory = 2GB

# Submit
queue
"""


def generate_run_script(fit_dir: Path) -> str:
    """
    Generate fit execution script

    Args:
        fit_dir: Absolute path to fit directory

    Returns:
        Bash script content
    """
    fit_dir = fit_dir.resolve()  # Ensure absolute path
    config_dir = fit_dir / "config"
    repo_root = Path(__file__).parent.parent.parent.resolve()
    setup_env = repo_root / "setup_env.sh"

    return f"""#!/bin/bash
# xFitter fit execution script
set -e

CONFIGDIR="{config_dir}"
source "{setup_env}"

# flexiblas shim (condor nodes miss libflexiblas, map to openblas)
SHIM_DIR=$(mktemp -d)
trap "rm -rf $SHIM_DIR" EXIT
ln -s /cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc13-opt/lib/libopenblas.so \\
      "$SHIM_DIR/libflexiblas.so.3"
export LD_LIBRARY_PATH="$SHIM_DIR:$LD_LIBRARY_PATH"

cd "$CONFIGDIR"
xfitter
"""


def generate_condor_wrapper(fits_dir: Path) -> Path:
    """
    Generate master Condor submission wrapper for all fits in scan

    Args:
        fits_dir: Path to fits/ directory containing fit subdirectories

    Returns:
        Path to generated wrapper script
    """
    wrapper_script = fits_dir / "condor_submit_all.sh"

    # Find all fit subdirectories
    fit_subdirs = sorted([d for d in fits_dir.iterdir() if d.is_dir()])

    script_content = """#!/bin/bash
# Master Condor submission script for scan
# Generated automatically

set -e

SCAN_DIR="$(pwd)"
echo "Submitting all fits in: $SCAN_DIR"
echo "Number of fits: {num_fits}"
echo ""

""".format(num_fits=len(fit_subdirs))

    for fit_subdir in fit_subdirs:
        script_content += f"""
# Submit {fit_subdir.name}
echo "Submitting {fit_subdir.name}..."
cd {fit_subdir.name}/condor
condor_submit job.sub
cd "$SCAN_DIR"
"""

    script_content += """
echo ""
echo "All fits submitted. Monitor with: condor_q"
"""

    wrapper_script.write_text(script_content)
    wrapper_script.chmod(0o755)

    return wrapper_script
