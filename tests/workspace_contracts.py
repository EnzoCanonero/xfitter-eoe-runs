"""Shared support for generated Condor workspace contract tests."""

import contextlib
import io
import os
import re
import shlex
import subprocess
import textwrap
import unittest
from pathlib import Path

from xfitter_eoe_runs.scans.runner import run_scan


REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_TEMPLATES = REPO_ROOT / "templates"
NEW_FIT = REPO_ROOT / "scripts" / "new-fit"


FAKE_CONDOR_SUBMIT = r'''#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path


def fail(message):
    print(f"fake condor_submit: {message}", file=sys.stderr)
    raise SystemExit(2)


def required_field(text, name):
    match = re.search(rf"^{re.escape(name)}\s*=\s*(.*?)\s*$", text, re.MULTILINE)
    if match is None or not match.group(1):
        fail(f"missing field: {name}")
    return match.group(1)


def local_data_files(config_dir):
    steering = (config_dir / "steering.txt").read_text()
    names = re.findall(r"['\"]([^'\"]+\.dat)['\"]", steering)
    count = re.search(r"\bNInputFiles\s*=\s*(\d+)", steering)
    if (
        count is None
        or not names
        or int(count.group(1)) != len(names)
        or len(names) != len(set(names))
    ):
        fail(f"NInputFiles does not match unique dataset entries in {config_dir / 'steering.txt'}")
    for name in names:
        if Path(name).name != name:
            fail(f"dataset is not local to the worker: {name}")
        data_file = config_dir / name
        if not data_file.is_file() or data_file.stat().st_size == 0:
            fail(f"missing or empty dataset: {data_file}")


def validate_workspace(fit_dir):
    fit_dir = fit_dir.resolve()
    config_dir = fit_dir / "config"
    for directory in (config_dir, fit_dir / "output", fit_dir / "condor" / "logs"):
        if not directory.is_dir():
            fail(f"missing directory: {directory}")

    for name in ("steering.txt", "parameters.yaml", "constants.yaml", "unpolarised.wgt"):
        path = config_dir / name
        if not path.is_file() or path.stat().st_size == 0:
            fail(f"missing or empty worker input: {path}")
    local_data_files(config_dir)

    parameters = (config_dir / "parameters.yaml").read_text()
    matches = re.findall(
        r'^OutputDirectory:\s*["\']?([^"\'\n]+?)["\']?\s*$',
        parameters,
        re.MULTILINE,
    )
    if len(matches) != 1:
        fail(f"expected one OutputDirectory in {config_dir / 'parameters.yaml'}")
    output_dir = Path(matches[0].strip())
    if not output_dir.is_absolute() or output_dir.resolve() != (fit_dir / "output").resolve():
        fail(f"incorrect OutputDirectory for {fit_dir}: {output_dir}")


if len(sys.argv) != 2:
    fail("expected exactly one submit descriptor")

submit_file = Path(sys.argv[1])
if not submit_file.is_absolute() or not submit_file.is_file():
    fail(f"submit descriptor is missing or not absolute: {submit_file}")
text = submit_file.read_text()

if required_field(text, "universe") != "vanilla":
    fail("only the vanilla universe is expected")
if required_field(text, "should_transfer_files") != "NO":
    fail("workers must use the shared filesystem")
for field in ("request_cpus", "request_memory"):
    required_field(text, field)

executable = Path(required_field(text, "executable"))
if not executable.is_absolute() or not executable.is_file() or not os.access(executable, os.X_OK):
    fail(f"worker executable is missing, relative, or not executable: {executable}")

queue_lines = [
    line.strip()
    for line in text.splitlines()
    if line.strip().lower().startswith("queue")
]
if len(queue_lines) != 1:
    fail("expected exactly one queue statement")

if queue_lines[0] == "queue 1":
    batch_job = False
    if re.search(r'^arguments\s*=', text, re.MULTILINE):
        fail("single-fit job unexpectedly has arguments")
    initial_dir = Path(required_field(text, "initialdir"))
    fit_dirs = [initial_dir.parent]
else:
    batch_job = True
    queue_match = re.fullmatch(r"queue\s+fitdir\s+from\s+(.+)", queue_lines[0])
    if queue_match is None:
        fail(f"unsupported queue statement: {queue_lines[0]}")
    if required_field(text, "arguments") != "$(fitdir)":
        fail("batch worker argument must be $(fitdir)")
    manifest = Path(queue_match.group(1))
    if not manifest.is_absolute() or not manifest.is_file():
        fail(f"fit manifest is missing or not absolute: {manifest}")
    manifest_lines = [line.strip() for line in manifest.read_text().splitlines() if line.strip()]
    if not manifest_lines or len(manifest_lines) != len(set(manifest_lines)):
        fail("fit manifest must be non-empty and contain unique entries")
    fit_dirs = [Path(line) for line in manifest_lines]
    if any(not path.is_absolute() for path in fit_dirs):
        fail("all fit manifest entries must be absolute")

if batch_job:
    expected_executable = submit_file.parent / "run_fit.sh"
else:
    expected_executable = fit_dirs[0] / "condor" / "run_fit.sh"
if executable.resolve() != expected_executable.resolve():
    fail(f"unexpected worker executable: {executable}")

for fit_dir in fit_dirs:
    fit_dir = fit_dir.resolve()
    substitutions = {"$(fitdir)": str(fit_dir)}
    expanded = {}
    for field in ("initialdir", "output", "error", "log"):
        value = required_field(text, field)
        for macro, replacement in substitutions.items():
            value = value.replace(macro, replacement)
        expanded[field] = Path(value)
        if not expanded[field].is_absolute():
            fail(f"{field} is not absolute for {fit_dir}: {expanded[field]}")

    if expanded["initialdir"].resolve() != (fit_dir / "config").resolve():
        fail(f"initialdir does not select the fit config: {expanded['initialdir']}")
    expected_log_dir = fit_dir / "condor" / "logs"
    expected_paths = {
        "output": expected_log_dir / "output.log",
        "error": expected_log_dir / "error.log",
        "log": submit_file.parent / "batch.log" if batch_job else expected_log_dir / "run.log",
    }
    for field, expected in expected_paths.items():
        if expanded[field].resolve() != expected.resolve() or not expanded[field].parent.is_dir():
            fail(f"incorrect path for {field}: {expanded[field]}")
    validate_workspace(fit_dir)

log_file = os.environ.get("FAKE_CONDOR_LOG")
if not log_file:
    fail("FAKE_CONDOR_LOG is not set")
with open(log_file, "a") as handle:
    handle.write(str(submit_file.resolve()) + "\n")
'''


FAKE_XFITTER = r'''#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path


def fail(message):
    print(f"fake xfitter: {message}", file=sys.stderr)
    raise SystemExit(3)


if len(sys.argv) != 1:
    fail(f"unexpected arguments: {sys.argv[1:]}")
if os.environ.get("XFITTER_TEST_SETUP") != "loaded":
    fail("the worker setup script was not sourced")

config_dir = Path.cwd().resolve()
if config_dir.name != "config":
    fail(f"working directory is not a fit config directory: {config_dir}")
fit_dir = config_dir.parent
output_dir = fit_dir / "output"

for name in ("steering.txt", "parameters.yaml", "constants.yaml", "unpolarised.wgt"):
    path = config_dir / name
    if not path.is_file() or path.stat().st_size == 0 or not os.access(path, os.R_OK):
        fail(f"missing, empty, or unreadable input: {path}")

steering = (config_dir / "steering.txt").read_text()
datasets = re.findall(r"['\"]([^'\"]+\.dat)['\"]", steering)
count = re.search(r"\bNInputFiles\s*=\s*(\d+)", steering)
if count is None or not datasets or int(count.group(1)) != len(datasets):
    fail("NInputFiles does not match the declared datasets")
if len(datasets) != len(set(datasets)):
    fail("steering.txt declares duplicate datasets")
for name in datasets:
    if Path(name).name != name:
        fail(f"dataset path is not local: {name}")
    path = config_dir / name
    if not path.is_file() or path.stat().st_size == 0 or not os.access(path, os.R_OK):
        fail(f"missing, empty, or unreadable dataset: {path}")

parameters = (config_dir / "parameters.yaml").read_text()
matches = re.findall(
    r'^OutputDirectory:\s*["\']?([^"\'\n]+?)["\']?\s*$',
    parameters,
    re.MULTILINE,
)
if len(matches) != 1:
    fail("parameters.yaml must contain exactly one OutputDirectory")
configured_output = Path(matches[0].strip())
if not configured_output.is_absolute() or configured_output.resolve() != output_dir.resolve():
    fail(f"OutputDirectory does not point to the fit output: {configured_output}")
if not output_dir.is_dir():
    fail(f"output directory is missing: {output_dir}")

shim_paths = [
    Path(entry) / "libflexiblas.so.3"
    for entry in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep)
    if entry
]
if not shim_paths or not shim_paths[0].is_symlink():
    fail("the worker did not prepare the FlexiBLAS shim")

probe = output_dir / ".xfitter-contract-write-probe"
try:
    probe.write_text("writable\n")
    probe.unlink()
except OSError as error:
    fail(f"output directory is not writable: {error}")

(output_dir / "Results.txt").write_text("fake xFitter results\n")
(output_dir / "minuit.out.txt").write_text("fake xFitter MINUIT output\n")
(output_dir / "xfitter-contract.ok").write_text(
    f"cwd={config_dir}\nsetup={os.environ['XFITTER_TEST_SETUP']}\n"
)
'''


def _write_executable(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(0o755)


def install_fake_runtime(root, setup_env=None):
    """Create validating Condor/xFitter executables and a sourceable setup."""
    fake_tree = root / "fake-xfitter-tree"
    fake_bin = fake_tree / "bin"
    fake_condor_bin = root / "fake-condor-bin"
    (fake_tree / "lib" / "xfitter").mkdir(parents=True)
    _write_executable(fake_bin / "xfitter", FAKE_XFITTER)
    _write_executable(fake_condor_bin / "condor_submit", FAKE_CONDOR_SUBMIT)

    setup_env = setup_env or root / "setup-env.sh"
    _write_executable(
        setup_env,
        textwrap.dedent(
            f"""\
            #!/bin/bash
            export XFITTER_TEST_SETUP=loaded
            export PATH={shlex.quote(str(fake_bin))}:$PATH
            export LD_LIBRARY_PATH="${{LD_LIBRARY_PATH:-}}"
            """
        ),
    )

    condor_log = root / "condor-submit.log"
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join((str(fake_condor_bin), "/usr/bin", "/bin"))
    environment["LD_LIBRARY_PATH"] = ""
    environment.pop("XFITTER_TEST_SETUP", None)
    environment["FAKE_CONDOR_LOG"] = str(condor_log)
    return setup_env, environment, condor_log


class WorkspaceContractTestCase(unittest.TestCase):
    """Assertions and fixtures shared by workspace contract test cases."""

    def run_checked(self, command, *, cwd=None, env=None):
        result = subprocess.run(
            [str(part) for part in command],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=(
                f"command failed ({result.returncode}): {' '.join(str(p) for p in command)}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            ),
        )
        return result

    def assert_shell_syntax(self, *scripts):
        for script in scripts:
            with self.subTest(shell_script=str(script)):
                self.run_checked(["bash", "-n", script])

    def assert_worker_outputs(self, fit_dir):
        output_dir = fit_dir / "output"
        for name in ("Results.txt", "minuit.out.txt", "xfitter-contract.ok"):
            output = output_dir / name
            self.assertTrue(output.is_file(), output)
            self.assertGreater(output.stat().st_size, 0, output)
        marker = (output_dir / "xfitter-contract.ok").read_text()
        self.assertIn(f"cwd={(fit_dir / 'config').resolve()}", marker)
        self.assertIn("setup=loaded", marker)

    def generate_scan_workspace(self, root, name, config, expected_relative_paths):
        dataset_root = root / "datasets"
        dataset_root.mkdir(exist_ok=True)
        dataset = dataset_root / "toy.dat"
        dataset.write_text("toy dataset\n")
        setup_env, environment, condor_log = install_fake_runtime(root)

        workspace = root / name
        workspace.mkdir()
        (workspace / "config.yaml").write_text(textwrap.dedent(config))
        with self.subTest(generate=name), contextlib.redirect_stdout(io.StringIO()):
            run_scan(
                workspace,
                template_root=SCAN_TEMPLATES,
                dataset_root=dataset_root,
                setup_env=setup_env,
                submit=False,
            )

        expected = [
            (workspace / "runs" / relative).resolve()
            for relative in expected_relative_paths
        ]
        manifest = workspace / "runs" / "batch" / "fit_dirs.txt"
        queued = [Path(line) for line in manifest.read_text().splitlines() if line]
        self.assertEqual(queued, expected)
        actual = sorted(
            steering.parent.parent.resolve()
            for steering in (workspace / "runs").glob("**/config/steering.txt")
        )
        self.assertEqual(actual, sorted(expected))
        for fit_dir in expected:
            self.assertEqual(
                (fit_dir / "config" / "toy.dat").read_bytes(),
                dataset.read_bytes(),
            )
        return workspace, expected, environment, condor_log

    def submit_and_run_scan(self, workspace, fit_dirs, environment, condor_log):
        submit_script = workspace / "runs" / "submit.sh"
        batch_worker = workspace / "runs" / "batch" / "run_fit.sh"
        per_fit_submitters = [fit_dir / "condor" / "submit.sh" for fit_dir in fit_dirs]
        self.assert_shell_syntax(submit_script, batch_worker, *per_fit_submitters)

        prior_submissions = (
            condor_log.read_text().splitlines() if condor_log.exists() else []
        )
        with self.subTest(submit=workspace.name):
            self.run_checked(["bash", submit_script], cwd=workspace, env=environment)
        descriptor = (workspace / "runs" / "batch" / "condor_batch.sub").resolve()
        self.assertEqual(
            condor_log.read_text().splitlines(),
            prior_submissions + [str(descriptor)],
        )

        for fit_dir in fit_dirs:
            with self.subTest(worker=workspace.name, fit=str(fit_dir)):
                self.run_checked(
                    ["bash", batch_worker, fit_dir],
                    cwd=fit_dir / "config",
                    env=environment,
                )
                self.assert_worker_outputs(fit_dir)
