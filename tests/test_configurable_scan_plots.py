"""Plot selection regressions using small synthetic, non-HERA parameter sets."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
import yaml

from xfitter_eoe_runs.scans import plotter
from xfitter_eoe_runs.scans.config import load_study_config


REPO_ROOT = Path(__file__).resolve().parents[1]


class ConfigurableScanPlotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.addCleanup(plotter.plt.close, "all")

    def write_config(self, scan_type="lambda-scan", **overrides):
        data = {"scan_type": scan_type, "template": "hera-baseline"}
        if scan_type == "pumplin-stability":
            data.update(eps=0.6, **{
                "lambda": [1.0], "errdef": [0.5], "iterate": [10],
                "plot_parameters": ["shape_b", "amplitude"],
                "systematics": [
                    {"name": "calibration", "type": "E"},
                    {"name": "normalization", "type": "N"},
                    {"name": "amplitude", "type": "E"},
                    {"name": "detector", "type": "E", "range": "1-2"},
                ],
            })
        else:
            data.update(epsilon=0.6, systematics=[], **{
                "lambda": {"min": 0.0, "max": 1.0, "step": 1.0},
            })
        data.update(overrides)
        (self.root / "config.yaml").write_text(yaml.safe_dump(data))
        return load_study_config(self.root, REPO_ROOT / "templates")

    @staticmethod
    def synthetic_results():
        parameters = pd.DataFrame([
            {"lambda": 0.0, "parameter": "amplitude", "central_value": 10.0, "error": 2.0},
            {"lambda": 1.0, "parameter": "amplitude", "central_value": 8.0, "error": 0.8},
            {"lambda": 0.0, "parameter": "shape_b", "central_value": 1.0, "error": 0.5},
            {"lambda": 1.0, "parameter": "shape_b", "central_value": 3.0, "error": 0.1},
        ])
        chi2 = pd.DataFrame([
            {"lambda": 0.0, "chi2_corrected": 12.0, "ci_bartlett": 1.0, "converged": True},
            {"lambda": 1.0, "chi2_corrected": 10.0, "ci_bartlett": 2.5, "converged": True},
        ])
        return {"parameters": parameters, "chi2": chi2}

    def test_pumplin_uses_custom_parameter_order_and_appends_e_nuisances_once(self):
        config = self.write_config("pumplin-stability")
        self.assertEqual(plotter._pumplin_plot_params(config), [
            "shape_b", "amplitude", "calibration", "detector1", "detector2",
        ])
        self.assertEqual(config.plot_parameters, ["shape_b", "amplitude"])

    def test_comparison_uses_custom_labels_order_and_bartlett_intervals(self):
        results = self.synthetic_results()
        normalized = results["parameters"].copy()
        normalized["norm_value"] = [0.0, -1.0, 0.0, 4.0]
        normalized["norm_error"] = [1.0, 0.4, 1.0, 0.2]
        selected = [("shape_b", "Shape coefficient"), ("amplitude", "Amplitude")]

        with mock.patch("matplotlib.figure.Figure.savefig", autospec=True) as save:
            with contextlib.redirect_stdout(io.StringIO()):
                plotter._plot_parameter_comparison(
                    normalized, results["chi2"], self.root, selected,
                )

        save.assert_called_once()
        fig, output = save.call_args.args[:2]
        self.assertEqual(output, self.root / "7_parameter_comparison.pdf")
        axis = fig.axes[0]
        self.assertEqual(
            [tick.get_text() for tick in axis.get_yticklabels()],
            ["Shape coefficient", "Amplitude"],
        )
        intervals = axis.containers[0]
        np.testing.assert_allclose(intervals.lines[0].get_xdata(), [4.0, -1.0])
        np.testing.assert_allclose(
            intervals.lines[2][0].get_segments(),
            [[[3.5, 0.0], [4.5, 0.0]], [[-2.0, 1.0], [0.0, 1.0]]],
        )

    def test_comparison_skips_missing_selected_parameter_with_clear_message(self):
        results = self.synthetic_results()
        with mock.patch("matplotlib.figure.Figure.savefig") as save:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                plotter._plot_parameter_comparison(
                    results["parameters"], results["chi2"], self.root,
                    [("unmeasured_shape", "Unmeasured shape")],
                )
        save.assert_not_called()
        self.assertIn("unmeasured_shape", output.getvalue())
        self.assertIn("Skipping", output.getvalue())

    def test_lambda_comparison_is_disabled_when_selection_is_omitted_or_empty(self):
        for kwargs in ({}, {"parameter_comparison": []}):
            with self.subTest(kwargs=kwargs):
                with mock.patch("matplotlib.figure.Figure.savefig") as save, \
                        mock.patch.object(plotter, "PdfPages"), \
                        mock.patch("matplotlib.figure.Figure.tight_layout"), \
                        contextlib.redirect_stdout(io.StringIO()):
                    plotter._plot_lambda_scan(self.synthetic_results(), self.root, **kwargs)
                outputs = [call.args[0].name for call in save.call_args_list]
                self.assertIn("1_chi2_vs_lambda.pdf", outputs)
                self.assertNotIn("7_parameter_comparison.pdf", outputs)

    def test_lambda_scan_passes_normalized_values_and_custom_selection(self):
        selected = [("shape_b", "Shape coefficient"), ("amplitude", "Amplitude")]
        with mock.patch.object(plotter, "_plot_parameter_comparison") as comparison:
            with mock.patch("matplotlib.figure.Figure.savefig"), \
                    mock.patch.object(plotter, "PdfPages"), \
                    mock.patch("matplotlib.figure.Figure.tight_layout"), \
                    contextlib.redirect_stdout(io.StringIO()):
                plotter._plot_lambda_scan(
                    self.synthetic_results(), self.root,
                    parameter_comparison=selected, font_size_offset=2,
                )

        comparison.assert_called_once()
        normalized = comparison.call_args.args[0]
        eoe = normalized[normalized["lambda"] == 1.0].set_index("parameter")
        self.assertAlmostEqual(eoe.loc["shape_b", "norm_value"], 4.0)
        self.assertAlmostEqual(eoe.loc["amplitude", "norm_error"], 0.4)
        self.assertEqual(comparison.call_args.kwargs["parameter_labels"], selected)
        self.assertEqual(comparison.call_args.kwargs["font_size_offset"], 2)

    def test_plot_scan_reads_comparison_selection_from_workspace_config(self):
        self.write_config(parameter_comparison=[
            {"name": "shape_b", "label": "Shape coefficient"},
            {"name": "amplitude"},
        ])
        with mock.patch.object(plotter, "extract_scan_results", return_value=self.synthetic_results()):
            with mock.patch.object(plotter, "_plot_lambda_scan") as plot:
                with contextlib.redirect_stdout(io.StringIO()):
                    plotter.plot_scan(self.root, REPO_ROOT / "templates")
        self.assertEqual(plot.call_args.kwargs["parameter_comparison"], [
            ("shape_b", "Shape coefficient"), ("amplitude", "amplitude"),
        ])


if __name__ == "__main__":
    unittest.main()
