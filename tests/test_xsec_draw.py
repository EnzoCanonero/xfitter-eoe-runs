"""Tests for selecting the xFitter drawing executable."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from xfitter_eoe_runs.comparisons.xsec_draw import _find_xfitter_draw


class XfitterDrawSelectionTests(unittest.TestCase):
    @staticmethod
    def _make_draw(root: Path, tree: str) -> Path:
        executable = root / tree / "bin" / "xfitter-draw"
        executable.parent.mkdir(parents=True)
        executable.write_text("#!/bin/bash\n")
        executable.chmod(0o755)
        return executable

    def test_fresh_comparison_defaults_to_relocated_master(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            expected = self._make_draw(root, "merge-master/xfitter-master")
            with patch.dict(
                    os.environ,
                    {"XFITTER_ROOT": str(root)},
                    clear=True):
                self.assertEqual(_find_xfitter_draw({}), str(expected))

    def test_config_tree_overrides_environment_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_draw(root, "environment-tree")
            expected = self._make_draw(root, "configured-tree")
            with patch.dict(
                    os.environ,
                    {
                        "XFITTER_ROOT": str(root),
                        "XFITTER_TREE": "environment-tree",
                    },
                    clear=True):
                self.assertEqual(
                    _find_xfitter_draw({"xfitter_tree": "configured-tree"}),
                    str(expected),
                )

    def test_absolute_config_tree_overrides_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            expected = self._make_draw(root, "historical-tree")
            with patch.dict(os.environ, {"XFITTER_ROOT": "/missing",
                                         "XFITTER_TREE": "other-tree"}, clear=True):
                self.assertEqual(
                    _find_xfitter_draw({"xfitter_tree": str(root / "historical-tree")}),
                    str(expected),
                )

    def test_missing_selected_tree_does_not_fall_back_to_path(self):
        for selection in ("config", "environment", "default"):
            with self.subTest(selection=selection), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                stale = self._make_draw(root, "stale-tree")
                environment = {"XFITTER_ROOT": str(root), "PATH": str(stale.parent)}
                config = {}
                if selection == "config":
                    config["xfitter_tree"] = "missing-tree"
                    environment["XFITTER_TREE"] = "stale-tree"
                elif selection == "environment":
                    environment["XFITTER_TREE"] = "missing-tree"
                with patch.dict(os.environ, environment, clear=True):
                    with self.assertRaisesRegex(FileNotFoundError, "selected xFitter tree"):
                        _find_xfitter_draw(config)

    def test_selected_binary_must_be_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executable = self._make_draw(root, "selected-tree")
            executable.chmod(0o644)
            with patch.dict(os.environ, {"XFITTER_ROOT": str(root)}, clear=True):
                with self.assertRaisesRegex(FileNotFoundError, "no executable"):
                    _find_xfitter_draw({"xfitter_tree": "selected-tree"})


class PlotXsecEnvironmentTests(unittest.TestCase):
    def _run_wrapper(self, setup_text):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "scripts"
            scripts.mkdir()
            launcher = scripts / "plot-xsec"
            shutil.copy2(Path(__file__).resolve().parents[1] / "scripts" / "plot-xsec",
                         launcher)
            (scripts / "setup-env.sh").write_text(setup_text)
            binary_dir = root / "bin"
            binary_dir.mkdir()
            for name, body in (
                ("xfitter-draw", "exit 0\n"),
                ("python3", 'printf "setup=%s\\n" "${DRAW_SETUP_MARKER-unset}"\n'),
            ):
                executable = binary_dir / name
                executable.write_text("#!/bin/bash\n" + body)
                executable.chmod(0o755)
            environment = dict(os.environ)
            environment.pop("DRAW_SETUP_MARKER", None)
            environment["PATH"] = str(binary_dir) + os.pathsep + os.environ["PATH"]
            return subprocess.run(["bash", str(launcher), "unused-workspace"],
                                  env=environment, capture_output=True, text=True)

    def test_existing_draw_on_path_does_not_skip_setup(self):
        result = self._run_wrapper("export DRAW_SETUP_MARKER=initialized\n")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("setup=initialized", result.stdout)

    def test_setup_failure_stops_before_python_even_with_draw_on_path(self):
        result = self._run_wrapper("return 1\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("failed to initialize the requested xFitter build", result.stderr)
        self.assertNotIn("setup=", result.stdout)


if __name__ == "__main__":
    unittest.main()
