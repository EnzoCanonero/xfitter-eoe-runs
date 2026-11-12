"""Likelihood generation without pre-existing fit outputs."""

import contextlib
import io
import json
import re
import tempfile
from pathlib import Path

import yaml

from tests.workspace_contracts import WorkspaceContractTestCase, SCAN_TEMPLATES
from xfitter_eoe_runs.scans.runner import run_scan


CONFIG = """\
scan_type: likelihood-scan
template: hera-baseline
dataset_root: ../datasets
datafiles: [toy.dat]
epsilon: 0.6
parameter_overrides:
  ADbar: {value: 0.33, step: 0.02}
  CDbar: {value: 9.0, step: 0.5}
systematics:
  - {name: sysHZComb1053, type: E, init: -1.0}
  - {name: proc_tb21, type: E, init: 0.5}
  - {name: sysHZComb1064, type: E, init: 2.0}
scan_params_1d:
  - {name: ADbar, min: 0.2, max: 0.4, npoints: 2}
scan_systematics_1d:
  - {name: sysHZComb1064, min: -1.0, max: 1.0, npoints: 2}
scan_params_2d:
  - pair: [CDbar, sysHZComb1053]
    x_range: [8, 10]
    y_range: [-2, 2]
    npoints: [2, 3]
"""


def parameter_file(fit_dir):
    text = (fit_dir / 'config/parameters.yaml').read_text()
    block = re.search(r'^Parameters:\n.*?(?=^\S|\Z)', text, re.M | re.S)
    return yaml.safe_load(block.group())['Parameters'], text


class LikelihoodScanWorkspaceTests(WorkspaceContractTestCase):
    def test_nominal_and_manual_grids_submit_and_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = ['nominal', '1d_ADbar_000', '1d_ADbar_001',
                     '1d_sysHZComb1064_000', '1d_sysHZComb1064_001']
            names += [f'2d_CDbar_sysHZComb1053_{i:03d}_{j:03d}'
                      for i in range(2) for j in range(3)]
            workspace, fit_dirs, environment, condor_log = self.generate_scan_workspace(
                root, 'likelihood', CONFIG, names,
            )
            nominal, text = parameter_file(fit_dirs[0])
            self.assertEqual(nominal['ADbar'], [0.33, 0.02])
            self.assertEqual(nominal['CDbar'], {'value': 9.0, 'step': 0.5})
            self.assertNotIn('    fix ', text)
            self.assertIn('    set par 25 2\n', text)
            for fit_dir, value in zip(fit_dirs[1:3], [0.2, 0.4]):
                params, _ = parameter_file(fit_dir)
                self.assertEqual(params['ADbar'], [value, 0])
            _, text = parameter_file(fit_dirs[3])
            self.assertIn('    set par 25 -1\n    fix 25\n', text)
            self.assertNotIn('    set par 25 2\n', text)
            params, text = parameter_file(fit_dirs[5])
            self.assertEqual(params['CDbar'], {'value': 8.0, 'step': 0.0})
            self.assertIn('    set par 23 -2\n    fix 23\n', text)
            self.assertIn('    set par 25 2\n', text)
            manifest = json.loads((workspace / 'runs/scan_manifest.json').read_text())
            self.assertEqual(manifest['nominal'], 'nominal')
            self.assertEqual(manifest['scan_1d']['ADbar']['scan_values'], [0.2, 0.4])
            self.submit_and_run_scan(workspace, fit_dirs, environment, condor_log)

    def test_preview_needs_no_outputs_and_rejects_old_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / 'study'
            workspace.mkdir()
            (root / 'datasets').mkdir()
            (root / 'datasets/toy.dat').write_text('toy data\n')
            config = workspace / 'config.yaml'
            config.write_text(CONFIG)
            with contextlib.redirect_stdout(io.StringIO()):
                run_scan(workspace, SCAN_TEMPLATES, None, root / 'setup-env.sh', dry_run=True)
            self.assertFalse((workspace / 'runs').exists())
            config.write_text(CONFIG + 'reference_fit: ../old-fit\n')
            with self.assertRaisesRegex(ValueError, 'unsupported likelihood'):
                run_scan(workspace, SCAN_TEMPLATES, None, root / 'setup-env.sh', dry_run=True)
