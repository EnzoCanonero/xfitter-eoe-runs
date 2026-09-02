"""Workspace contract test for Pumplin-stability studies."""

import tempfile
from pathlib import Path

from tests.workspace_contracts import WorkspaceContractTestCase


class PumplinStabilityWorkspaceTests(WorkspaceContractTestCase):
    def test_pumplin_stability_workspace_submits_and_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = (
                "scan_type: pumplin-stability\n"
                "template: hera-baseline\n"
                "eps: 0.6\n"
                "lambda: [1.0]\n"
                "errdef: [0.5]\n"
                "iterate: [10]\n"
                "datafiles: [toy.dat]\n"
                "systematics:\n"
                "  - {name: toy_source, type: E}\n"
            )
            workspace, fit_dirs, environment, condor_log = (
                self.generate_scan_workspace(
                    root,
                    "pumplin",
                    config,
                    [
                        "lambda_0.0/errdef0p5_iter10",
                        "lambda_1.0/errdef0p5_iter10",
                    ],
                )
            )

            gaussian, source = fit_dirs
            self.assertNotIn(
                "&Systematics",
                (gaussian / "config" / "steering.txt").read_text(),
            )
            self.assertIn(
                "'toy_source:E@eps=0.6'",
                (source / "config" / "steering.txt").read_text(),
            )
            for fit_dir in (gaussian, source):
                parameters = (fit_dir / "config" / "parameters.yaml").read_text()
                self.assertIn("Pumplin", parameters)
                self.assertIn("SET ERRDEF 0.5", parameters)
                self.assertIn("ITERATE 10", parameters)

            self.submit_and_run_scan(
                workspace,
                fit_dirs,
                environment,
                condor_log,
            )
