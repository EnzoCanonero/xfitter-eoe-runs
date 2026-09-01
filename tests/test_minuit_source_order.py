"""Regression tests for ordered resolution of truncated MINUIT source names."""

import tempfile
import unittest
import warnings
from pathlib import Path

from scans.lib.extract import (
    _resolve_ordered_minuit_definitions,
    extract_pumplin_widths,
)
from scans.lib.runner import (
    _build_reference_params,
    _order_systematics_by_e_reference,
    _reference_e_source_order,
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


def _steering(source_names):
    specs = ", ".join(f"'{name}:E@eps=0.6'" for name in source_names)
    return (
        "&Systematics\n"
        f"  ListOfSources = {specs}\n"
        "  n_iterations = 2\n"
        "&End\n"
    )


def _minuit_output(source_names):
    definition_lines = ["  1 'Bg        ' 0.0"]
    parameter_lines = ["  1 Bg 1.5 0.2"]
    for index, name in enumerate(source_names, start=23):
        definition_lines.append(f" {index:2d} '{name[:10]:10s}' 0.0")
        parameter_lines.append(f" {index:2d} {name[:10]} {index + 0.25:.2f} 0.10")
    return (
        "PARAMETER DEFINITIONS:\n"
        + "\n".join(definition_lines)
        + "\n**********\nEXT PARAMETER\n"
        + "\n".join(parameter_lines)
        + "\n\n"
    )


class LikelihoodReferenceOrderTests(unittest.TestCase):
    def test_reference_steering_order_resolves_nonalphabetical_hera_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            reference = Path(tmp)
            (reference / "config").mkdir()
            (reference / "output").mkdir()
            (reference / "config" / "steering.txt").write_text(_steering(HERA_SEVEN))
            (reference / "output" / "minuit.out.txt").write_text(
                _minuit_output(HERA_SEVEN)
            )

            # Deliberately supply a different configuration order. The exact set
            # agrees, so the reference ListOfSources order must remain authoritative.
            params = _build_reference_params(reference, sorted(HERA_SEVEN))

            for index, name in enumerate(HERA_SEVEN, start=23):
                self.assertEqual(params[name]["index"], index)
                self.assertEqual(params[name]["value"], index + 0.25)

            configured = [
                {"name": name, "type": "E", "epsilon": 0.6}
                for name in sorted(HERA_SEVEN)
            ]
            generated = _order_systematics_by_e_reference(configured, HERA_SEVEN)
            self.assertEqual([source["name"] for source in generated], HERA_SEVEN)

    def test_available_reference_with_mismatched_source_set_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            reference = Path(tmp)
            (reference / "config").mkdir()
            (reference / "config" / "steering.txt").write_text(
                _steering(HERA_SEVEN[:-1])
            )

            with self.assertRaisesRegex(ValueError, "E-source mismatch"):
                _reference_e_source_order(reference, HERA_SEVEN)

    def test_missing_reference_steering_warns_and_preserves_config_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                order = _reference_e_source_order(Path(tmp), HERA_SEVEN)

            self.assertEqual(order, HERA_SEVEN)
            self.assertEqual(len(caught), 1)
            self.assertIn("falling back", str(caught[0].message))


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
