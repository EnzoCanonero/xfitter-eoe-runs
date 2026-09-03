"""Smoke tests for the packaged plotting command adapters."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_MODULES = (
    "xfitter_eoe_runs.cli.plot_scan",
    "xfitter_eoe_runs.cli.plot_pdf_comparison",
    "xfitter_eoe_runs.cli.plot_xsec",
)
LAUNCHERS = (
    REPO_ROOT / "scripts" / "plot-scan",
    REPO_ROOT / "scripts" / "plot-pdf-comparison",
    REPO_ROOT / "scripts" / "plot-xsec",
)


class CliEntrypointTests(unittest.TestCase):
    def test_installed_modules_expose_help_without_external_runtimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            for module in CLI_MODULES:
                with self.subTest(module=module):
                    result = subprocess.run(
                        [sys.executable, "-I", "-m", module, "--help"],
                        cwd=tmp,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(
                        result.returncode,
                        0,
                        msg=result.stdout + result.stderr,
                    )
                    self.assertIn("usage:", result.stdout.lower())

    def test_shell_launchers_have_valid_syntax(self):
        for launcher in LAUNCHERS:
            with self.subTest(launcher=launcher.name):
                result = subprocess.run(
                    ["bash", "-n", launcher],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    msg=result.stdout + result.stderr,
                )


if __name__ == "__main__":
    unittest.main()
