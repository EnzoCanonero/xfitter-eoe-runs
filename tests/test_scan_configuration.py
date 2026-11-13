"""Study-specific dataset and plot configuration, independent of HERA inputs."""

import contextlib
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import yaml

from xfitter_eoe_runs.scans.config import load_study_config
from xfitter_eoe_runs.scans.runner import run_scan


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = REPO_ROOT / "templates"
MISSING = object()


class ScanConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "study"
        self.workspace.mkdir()

    def write_config(self, scan_type="lambda-scan", **overrides):
        data = {
            "scan_type": scan_type,
            "template": "hera-baseline",
            "datafiles": ["collider-observations.dat"],
            "systematics": [{"name": "calibration", "type": "E"}],
        }
        if scan_type == "pumplin-stability":
            data.update(eps=0.6, **{
                "lambda": [1.0], "errdef": [0.5], "iterate": [10],
            })
        else:
            data.update(epsilon=0.6, **{
                "lambda": {"min": 1.0, "max": 1.0, "step": 1.0},
            })
        data.update(overrides)
        (self.workspace / "config.yaml").write_text(yaml.safe_dump(data))
        return load_study_config(self.workspace, TEMPLATES)

    def make_dataset(self, name="custom-data", contents="custom observations\n"):
        directory = self.root / name
        directory.mkdir()
        (directory / "collider-observations.dat").write_text(contents)
        return directory

    def generate(self, dataset_root=None):
        with contextlib.redirect_stdout(io.StringIO()):
            run_scan(
                self.workspace, TEMPLATES, dataset_root,
                self.root / "setup-env.sh", submit=False,
            )

    def test_dataset_root_resolves_against_config_directory(self):
        config = self.write_config(dataset_root="../custom-data")
        self.assertEqual(config.dataset_root, self.root / "custom-data")

    def test_dataset_root_accepts_absolute_and_home_paths(self):
        for value, expected in (
            (str(self.root / "absolute-data"), self.root / "absolute-data"),
            ("~/scan-test-data", Path.home() / "scan-test-data"),
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    self.write_config(dataset_root=value).dataset_root,
                    expected.resolve(),
                )

    def test_dataset_root_rejects_missing_empty_and_non_string_values(self):
        for value in (MISSING, None, "", " \t", 1, False, [], {}):
            with self.subTest(value=value):
                config = self.write_config(
                    **({} if value is MISSING else {"dataset_root": value})
                )
                with self.assertRaisesRegex(ValueError, "dataset_root"):
                    _ = config.dataset_root

    def test_runner_uses_configured_custom_dataset(self):
        dataset = self.make_dataset()
        self.write_config(dataset_root="../custom-data")
        self.generate()
        fit_config = self.workspace / "runs" / "lambda_1.0" / "config"
        self.assertEqual(
            (fit_config / "collider-observations.dat").read_bytes(),
            (dataset / "collider-observations.dat").read_bytes(),
        )
        self.assertIn("collider-observations.dat", (fit_config / "steering.txt").read_text())

    def test_explicit_api_dataset_overrides_config_and_supports_old_configs(self):
        override = self.make_dataset("override", "explicit API observations\n")
        self.make_dataset("configured", "configuration observations\n")
        for value in (MISSING, "../configured", None):
            with self.subTest(value=value):
                self.write_config(
                    **({} if value is MISSING else {"dataset_root": value})
                )
                self.generate(override)
                generated = (
                    self.workspace / "runs" / "lambda_1.0" / "config"
                    / "collider-observations.dat"
                )
                self.assertEqual(generated.read_text(), "explicit API observations\n")

    def test_missing_dataset_directory_fails_before_creating_runs(self):
        self.write_config(dataset_root="../absent")
        with self.assertRaisesRegex(FileNotFoundError, "dataset_root"):
            self.generate()
        self.assertFalse((self.workspace / "runs").exists())

    def test_pumplin_plot_parameters_preserve_custom_order(self):
        config = self.write_config(
            "pumplin-stability", plot_parameters=["shape_b", "amplitude", "shape_a"],
        )
        self.assertEqual(config.plot_parameters, ["shape_b", "amplitude", "shape_a"])

    def test_pumplin_plot_parameters_reject_invalid_selections(self):
        invalid = (MISSING, None, [], "amplitude", {}, [""], [" "], [1],
                   ["amplitude", False], ["amplitude", "amplitude"])
        for value in invalid:
            with self.subTest(value=value):
                config = self.write_config(
                    "pumplin-stability",
                    **({} if value is MISSING else {"plot_parameters": value}),
                )
                with self.assertRaisesRegex(ValueError, "plot_parameters"):
                    _ = config.plot_parameters

    def test_pumplin_generation_does_not_require_plot_parameters(self):
        self.make_dataset()
        self.write_config("pumplin-stability", dataset_root="../custom-data")
        self.generate()
        for group in ("lambda_0.0", "lambda_1.0"):
            self.assertTrue((
                self.workspace / "runs" / group / "errdef0p5_iter10" / "config"
                / "collider-observations.dat"
            ).is_file())

    def test_lambda_parameter_comparison_defaults_to_disabled(self):
        for value in (MISSING, []):
            with self.subTest(value=value):
                config = self.write_config(
                    **({} if value is MISSING else {"parameter_comparison": value})
                )
                self.assertEqual(config.parameter_comparison, [])

    def test_lambda_parameter_comparison_preserves_order_and_defaults_labels(self):
        config = self.write_config(parameter_comparison=[
            {"name": "shape_b", "label": r"$b_{\mathrm{shape}}$"},
            {"name": "amplitude"},
        ])
        self.assertEqual(config.parameter_comparison, [
            ("shape_b", r"$b_{\mathrm{shape}}$"), ("amplitude", "amplitude"),
        ])

    def test_lambda_parameter_comparison_rejects_invalid_entries(self):
        invalid = (
            None, "amplitude", {}, ["amplitude"], [None], [{}],
            [{"name": ""}], [{"name": " "}], [{"name": 1}],
            [{"name": "amplitude", "label": None}],
            [{"name": "amplitude", "label": ""}],
            [{"name": "amplitude", "label": " "}],
            [{"name": "amplitude", "label": 1}],
            [{"name": "amplitude"}, {"name": "amplitude", "label": "Again"}],
        )
        for value in invalid:
            with self.subTest(value=value):
                config = self.write_config(parameter_comparison=value)
                with self.assertRaisesRegex(ValueError, "parameter_comparison"):
                    _ = config.parameter_comparison

    def test_run_scan_cli_uses_workspace_dataset_without_submitting(self):
        repo = self.root / "mini-repo"
        scripts = repo / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy2(REPO_ROOT / "scripts" / "run-scan", scripts / "run-scan")
        (repo / "src").symlink_to(REPO_ROOT / "src", target_is_directory=True)
        (repo / "templates").symlink_to(TEMPLATES, target_is_directory=True)
        self.workspace = repo / "runs" / "scans" / "custom-study"
        self.workspace.mkdir(parents=True)
        dataset = self.workspace / "observations"
        dataset.mkdir()
        (dataset / "collider-observations.dat").write_text("CLI custom dataset\n")
        self.write_config(dataset_root="observations")

        result = subprocess.run(
            [sys.executable, str(scripts / "run-scan"), str(self.workspace), "--no-submit"],
            cwd=self.root, capture_output=True, text=True,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        copied = (self.workspace / "runs" / "lambda_1.0" / "config"
                  / "collider-observations.dat")
        self.assertEqual(copied.read_text(), "CLI custom dataset\n")
        self.assertIn(str(dataset), result.stdout)
        self.assertNotIn("Submitting", result.stdout)


if __name__ == "__main__":
    unittest.main()
