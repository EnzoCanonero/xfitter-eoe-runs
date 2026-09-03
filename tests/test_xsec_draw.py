"""Tests for selecting the xFitter drawing executable."""

import os
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
        return executable

    def test_fresh_comparison_defaults_to_master(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            expected = self._make_draw(root, "xfitter-master")
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


if __name__ == "__main__":
    unittest.main()
