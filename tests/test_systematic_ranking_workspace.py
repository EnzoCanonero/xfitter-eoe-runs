"""Workspace contract test for systematic-ranking studies."""

import tempfile
from pathlib import Path

from tests.workspace_contracts import WorkspaceContractTestCase


class SystematicRankingWorkspaceTests(WorkspaceContractTestCase):
    def test_systematic_ranking_workspace_submits_and_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = (
                "scan_type: systematic-ranking\n"
                "template: hera-baseline\n"
                "epsilon: 0.6\n"
                "datafiles: [toy.dat]\n"
                "systematics:\n"
                "  - {name: toy_source, type: E}\n"
            )
            workspace, fit_dirs, environment, condor_log = (
                self.generate_scan_workspace(
                    root,
                    "ranking",
                    config,
                    ["nominal", "toy_source"],
                )
            )

            nominal, source = fit_dirs
            self.assertNotIn(
                "&Systematics",
                (nominal / "config" / "steering.txt").read_text(),
            )
            self.assertIn(
                "'toy_source:E@eps=0.6'",
                (source / "config" / "steering.txt").read_text(),
            )

            self.submit_and_run_scan(
                workspace,
                fit_dirs,
                environment,
                condor_log,
            )
