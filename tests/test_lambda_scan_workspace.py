"""Workspace contract test for lambda scans."""

import tempfile
from pathlib import Path

from tests.workspace_contracts import WorkspaceContractTestCase


class LambdaScanWorkspaceTests(WorkspaceContractTestCase):
    def test_lambda_scan_workspace_submits_and_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = (
                "scan_type: lambda-scan\n"
                "template: hera-baseline\n"
                "xfitter_tree: fake-xfitter-tree\n"
                f"xfitter_commit: {'a' * 40}\n"
                "epsilon: 0.6\n"
                "lambda: {min: 0.5, max: 0.5, step: 0.1}\n"
                "datafiles: [toy.dat]\n"
                "systematics:\n"
                "  - {name: toy_source, type: E}\n"
            )
            workspace, fit_dirs, environment, condor_log = (
                self.generate_scan_workspace(
                    root,
                    "lambda",
                    config,
                    ["lambda_0.5"],
                )
            )

            steering = (fit_dirs[0] / "config" / "steering.txt").read_text()
            self.assertIn("'toy_source:E@eps=0.3'", steering)

            worker = (workspace / "runs" / "batch" / "run_fit.sh").read_text()
            self.assertIn("export XFITTER_TREE=fake-xfitter-tree\n", worker)
            self.assertIn(f"export XFITTER_COMMIT={'a' * 40}\n", worker)
            self.assertLess(
                worker.index("export XFITTER_COMMIT="),
                worker.index('source "'),
            )
            per_fit_submitter = (fit_dirs[0] / "condor" / "submit.sh").read_text()
            self.assertIn("export XFITTER_TREE=fake-xfitter-tree\n", per_fit_submitter)
            self.assertIn(
                f"export XFITTER_COMMIT={'a' * 40}\n",
                per_fit_submitter,
            )

            self.submit_and_run_scan(
                workspace,
                fit_dirs,
                environment,
                condor_log,
            )
