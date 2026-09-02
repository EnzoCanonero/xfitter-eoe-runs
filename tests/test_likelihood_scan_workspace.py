"""Workspace contract test for profile-likelihood scans."""

import json
import tempfile
from pathlib import Path

from tests.workspace_contracts import WorkspaceContractTestCase


class LikelihoodScanWorkspaceTests(WorkspaceContractTestCase):
    def test_likelihood_scan_workspace_submits_and_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference_output = root / "reference" / "output"
            reference_output.mkdir(parents=True)
            (reference_output / "minuit.out.txt").write_text(
                "PARAMETER DEFINITIONS:\n"
                "  1 'ADbar     ' 0.0\n"
                "**********\n"
                "EXT PARAMETER\n"
                "  1 ADbar 0.3 0.1\n\n"
            )
            config = (
                "scan_type: likelihood-scan\n"
                "template: hera-baseline\n"
                "reference_fit: ../reference\n"
                "datafiles: [toy.dat]\n"
                "scan_params_1d:\n"
                "  - {name: ADbar, min: 0.2, max: 0.4, npoints: 2}\n"
            )
            workspace, fit_dirs, environment, condor_log = (
                self.generate_scan_workspace(
                    root,
                    "likelihood",
                    config,
                    ["1d_ADbar_000", "1d_ADbar_001"],
                )
            )

            for value, fit_dir in zip(("0.2", "0.4"), fit_dirs):
                parameters = (fit_dir / "config" / "parameters.yaml").read_text()
                self.assertIn(f"  ADbar: [ {value}, 0 ]", parameters)

            manifest = json.loads(
                (workspace / "runs" / "scan_manifest.json").read_text()
            )
            self.assertEqual(
                manifest["scan_1d"]["ADbar"]["scan_values"],
                [0.2, 0.4],
            )
            self.assertEqual(
                manifest["scan_1d"]["ADbar"]["fit_dirs"],
                ["1d_ADbar_000", "1d_ADbar_001"],
            )

            self.submit_and_run_scan(
                workspace,
                fit_dirs,
                environment,
                condor_log,
            )
