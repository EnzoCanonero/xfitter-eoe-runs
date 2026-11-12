"""Regression tests for ordered resolution of truncated MINUIT source names."""

import tempfile
import unittest
from pathlib import Path

from xfitter_eoe_runs.scans.extract import (
    _resolve_ordered_minuit_definitions,
    extract_pumplin_widths,
)
HERA_SEVEN = [
    "sysHZComb1053",
    "proc_tb21",
    "sysHZComb1064",
    "sysHZComb1114",
    "sysHZComb1144",
    "sysHZComb1111",
    "sysHZComb1113",
]


class PumplinOrderTests(unittest.TestCase):
    def test_repeated_prefixes_follow_definition_occurrence(self):
        definitions = {
            index: name[:10]
            for index, name in enumerate(HERA_SEVEN, start=23)
        }
        resolved = _resolve_ordered_minuit_definitions(definitions, HERA_SEVEN)
        self.assertEqual(
            [resolved[index] for index in sorted(resolved)],
            HERA_SEVEN,
        )

    def test_pumplin_widths_keep_configured_source_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp)
            output = runs / "lambda_1.0" / "errdef0p5_iter10" / "output"
            output.mkdir(parents=True)
            definitions = "\n".join(
                f" {index:2d} '{name[:10]:10s}' 0.0"
                for index, name in enumerate(HERA_SEVEN, start=23)
            )
            xranges = "\n".join(
                f"Par= {offset} TruePar= {index} at 0.0 +/- {index / 100:.2f}"
                for offset, index in enumerate(range(23, 30), start=1)
            )
            (output / "minuit.out.txt").write_text(
                "PARAMETER DEFINITIONS:\n"
                + definitions
                + "\n**********\n"
                + "XRANGE: find allowed displacements\n"
                + xranges
                + "\nERROR MATRIX FROM ITERATE\n"
            )

            widths, incomplete = extract_pumplin_widths(runs, HERA_SEVEN)

            self.assertEqual(incomplete, [])
            self.assertEqual(
                [name for name in HERA_SEVEN if (1.0, 0.5, 10, name) in widths],
                HERA_SEVEN,
            )
            for index, name in enumerate(HERA_SEVEN, start=23):
                self.assertAlmostEqual(widths[(1.0, 0.5, 10, name)], index / 100)

    def test_unordered_source_collection_is_rejected(self):
        with self.assertRaisesRegex(TypeError, "ordered sequence"):
            _resolve_ordered_minuit_definitions({23: "sysHZComb1"}, set(HERA_SEVEN))


if __name__ == "__main__":
    unittest.main()
