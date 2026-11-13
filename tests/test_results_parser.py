"""Regression tests for xFitter Results.txt format variants."""

import json
import math
import tempfile
import unittest
from pathlib import Path

from xfitter_eoe_runs.scans.extract import (
    ResultsParser,
    _extract_likelihood_scan_results,
)


class ResultsParserTests(unittest.TestCase):
    def parser_for(self, content):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        fit_dir = Path(temporary.name)
        output = fit_dir / "output"
        output.mkdir()
        (output / "Results.txt").write_text(content)
        return ResultsParser(fit_dir)

    def test_minimisation_heading_variants_and_scientific_numbers(self):
        cases = [
            ("Chi2 after minimisation +1.31333E+03 1129 1.0\n", 1313.33, 1129),
            ("after MINIMISATION -2.5d-01 42 3.0\n", -0.25, 42),
            ("  cHi2 AfTeR MiNiMiSaTiOn .75e+2 7 0.5\n", 75.0, 7),
        ]
        for content, chi2, ndf in cases:
            with self.subTest(content=content):
                parser = self.parser_for(content)
                self.assertAlmostEqual(parser.parse_chi2(), chi2)
                self.assertEqual(parser.parse_ndf(), ndf)

    def test_missing_heading_and_missing_ndf_remain_none(self):
        parser = self.parser_for("Corrected Chi2 1306.70\n")
        self.assertIsNone(parser.parse_chi2())
        self.assertIsNone(parser.parse_ndf())

        parser = self.parser_for("After minimisation 1.0e+03\n")
        self.assertEqual(parser.parse_chi2(), 1000.0)
        self.assertIsNone(parser.parse_ndf())

    def test_ordinary_systematic_shift_row(self):
        parser = self.parser_for(
            "    1  sysHZComb1002        -5.120E-01   +/-   +9.364d-01"
            "        :N:M:D\n"
        )

        shifts = parser.parse_systematic_shifts()

        self.assertEqual(len(shifts), 1)
        row = shifts.iloc[0]
        self.assertEqual(row["index"], 1)
        self.assertEqual(row["name"], "sysHZComb1002")
        self.assertAlmostEqual(row["shift"], -0.512)
        self.assertAlmostEqual(row["error"], 0.9364)
        self.assertEqual(row["sys_type"], ":N:M:D")
        for column in (
            "corr_err", "epsilon", "b_theta", "r", "b_tilde",
            "b_mutheta", "gof_contrib", "lr_contrib",
        ):
            self.assertIsNone(row[column])

    def test_current_extended_eoe_systematic_shift_row(self):
        parser = self.parser_for(
            "  23 sysHZComb1053 -2.5E-01 9.0E-01 8.0e-01 6.0e-01 "
            "7.0e-01 -2.0e-01 1.0e-01 1.1e+00 2.2e+00 :E:M:D\n"
        )

        shifts = parser.parse_systematic_shifts()

        self.assertEqual(len(shifts), 1)
        row = shifts.iloc[0]
        self.assertEqual(row["index"], 23)
        self.assertEqual(row["name"], "sysHZComb1053")
        self.assertAlmostEqual(row["shift"], -0.25)
        self.assertAlmostEqual(row["error"], 0.9)
        self.assertAlmostEqual(row["corr_err"], 0.8)
        self.assertAlmostEqual(row["epsilon"], 0.6)
        self.assertIsNone(row["b_theta"])
        self.assertAlmostEqual(row["r"], 0.7)
        self.assertAlmostEqual(row["b_tilde"], -0.2)
        self.assertAlmostEqual(row["b_mutheta"], 0.1)
        self.assertAlmostEqual(row["gof_contrib"], 1.1)
        self.assertAlmostEqual(row["lr_contrib"], 2.2)
        self.assertEqual(row["sys_type"], ":E:M:D")

    def test_compact_eoe_systematic_shift_row_remains_supported(self):
        parser = self.parser_for(
            "  24 proc_tb21 1.0 2.0 3.0 0.6 4.0 5.0 :E:M:D\n"
        )

        row = parser.parse_systematic_shifts().iloc[0]
        self.assertEqual(row["name"], "proc_tb21")
        self.assertAlmostEqual(row["b_theta"], 4.0)
        self.assertAlmostEqual(row["gof_contrib"], 5.0)
        self.assertIsNone(row["r"])
        self.assertIsNone(row["lr_contrib"])

    def test_likelihood_readers_accept_both_headings_and_keep_missing_nan(self):
        with tempfile.TemporaryDirectory() as tmp:
            fits_dir = Path(tmp)
            contents = {
                "nominal": "After minimisation 101.0 80 1.25\n",
                "legacy": "After minimisation 1.0e+02 80 1.25\n",
                "eoe": "cHi2 AFTER minimisation +1.025D+02 80 1.28\n",
            }
            for name, content in contents.items():
                output = fits_dir / name / "output"
                output.mkdir(parents=True)
                (output / "Results.txt").write_text(content)
                (output / "minuit.out.txt").write_text("MIGRAD MINIMIZATION HAS CONVERGED\n")

            (fits_dir / "missing" / "output").mkdir(parents=True)
            manifest = {
                "nominal": "nominal",
                "scan_1d": {
                    "ADbar": {
                        "scan_values": [0.2, 0.3, 0.4],
                        "fit_dirs": ["legacy", "eoe", "missing"],
                    },
                },
                "scan_2d": {
                    "ADbar__Bg": {
                        "x_name": "ADbar",
                        "y_name": "Bg",
                        "x_values": [0.2, 0.3, 0.4],
                        "y_values": [0.0],
                        "fit_grid": [["legacy"], ["eoe"], ["missing"]],
                    },
                },
            }
            (fits_dir / "scan_manifest.json").write_text(json.dumps(manifest))

            results = _extract_likelihood_scan_results(fits_dir)

            scan_1d = results["scan_1d"]["ADbar"]["chi2"]
            self.assertEqual(scan_1d[0], 100.0)
            self.assertEqual(scan_1d[1], 102.5)
            self.assertTrue(math.isnan(scan_1d[2]))

            scan_2d = results["scan_2d"]["ADbar__Bg"]["chi2"]
            self.assertEqual(scan_2d[0, 0], 100.0)
            self.assertEqual(scan_2d[1, 0], 102.5)
            self.assertTrue(math.isnan(scan_2d[2, 0]))
            self.assertEqual(results["nominal_chi2"], 101.0)
            self.assertEqual(results["scan_1d"]["ADbar"]["delta_chi2"][:2].tolist(), [-1, 1.5])
            self.assertEqual(results["scan_2d"]["ADbar__Bg"]["delta_chi2"][:2, 0].tolist(), [-1, 1.5])

            nominal_output = fits_dir / "nominal" / "output"
            for result_text, minuit_text in [
                ("After minimisation 101 80", "FCN=101 FROM MIGRAD STATUS=FAILED"),
                ("No result", "MIGRAD MINIMIZATION HAS CONVERGED"),
            ]:
                with self.subTest(nominal=result_text, status=minuit_text):
                    (nominal_output / "Results.txt").write_text(result_text)
                    (nominal_output / "minuit.out.txt").write_text(minuit_text)
                    with self.assertRaisesRegex(ValueError, "nominal fit"):
                        _extract_likelihood_scan_results(fits_dir)
            (nominal_output / "Results.txt").unlink()
            with self.assertRaisesRegex(ValueError, "nominal fit"):
                _extract_likelihood_scan_results(fits_dir)



if __name__ == "__main__":
    unittest.main()
