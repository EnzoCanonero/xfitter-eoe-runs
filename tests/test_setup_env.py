"""Contract tests for selecting and pinning an xFitter build tree."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SETUP_ENV = REPO_ROOT / "scripts" / "setup-env.sh"


class SetupEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.repo = self.root / "runs-repo"
        self.install = self.root / "xfitter-install"
        (self.repo / "scripts").mkdir(parents=True)
        self.install.mkdir()
        shutil.copy2(SETUP_ENV, self.repo / "scripts" / "setup-env.sh")

        self.default_commit = self._make_tree("default-tree")
        self.alternate_commit = self._make_tree("alternate-tree")

        (self.install / "setup.sh").write_text(
            'export PATH="$PWD/default-tree/bin:$PATH"\n'
            'export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}"\n'
        )
        self.lcg_setup = self.root / "lcg-setup.sh"
        self.lcg_setup.write_text("export XFITTER_TEST_LCG=loaded\n")
        (self.repo / ".env").write_text(
            f"XFITTER_ROOT={self.install}\n"
            "XFITTER_TREE=default-tree\n"
            f"XFITTER_COMMIT={self.default_commit}\n"
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _make_tree(self, name):
        tree = self.install / name
        (tree / "bin").mkdir(parents=True)
        executable = tree / "bin" / "xfitter"
        executable.write_text("#!/bin/bash\nexit 0\n")
        executable.chmod(0o755)
        (tree / "tracked.txt").write_text("clean\n")
        self._git(tree, "init", "-q")
        self._git(tree, "config", "user.name", "Test User")
        self._git(tree, "config", "user.email", "test@example.invalid")
        self._git(tree, "add", "bin/xfitter", "tracked.txt")
        self._git(tree, "commit", "-qm", "test tree")
        return self._git(tree, "rev-parse", "HEAD").stdout.strip()

    @staticmethod
    def _git(tree, *args):
        return subprocess.run(
            ["git", "-C", str(tree), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    def _source(self, **overrides):
        environment = os.environ.copy()
        environment.pop("XFITTER_TREE", None)
        environment.pop("XFITTER_COMMIT", None)
        environment.pop("XFITTER_SETUP_ROOT", None)
        environment["XFITTER_LCG_SETUP"] = str(self.lcg_setup)
        environment.update(overrides)
        return subprocess.run(
            [
                "bash",
                "-c",
                (
                    'source "$1" || exit $?\n'
                    'printf "tree=%s\\ncommit=%s\\nbinary=%s\\n" '
                    '"${XFITTER_TREE-unset}" "${XFITTER_COMMIT-unset}" '
                    '"$(command -v xfitter)"\n'
                ),
                "bash",
                str(self.repo / "scripts" / "setup-env.sh"),
            ],
            env=environment,
            capture_output=True,
            text=True,
        )

    def test_env_default_tree_and_commit_are_verified(self):
        result = self._source()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tree=default-tree\n", result.stdout)
        self.assertIn(f"commit={self.default_commit}\n", result.stdout)
        self.assertIn(
            f"binary={self.install / 'default-tree' / 'bin' / 'xfitter'}\n",
            result.stdout,
        )

    def test_caller_tree_and_commit_override_env_defaults(self):
        result = self._source(
            XFITTER_TREE="alternate-tree",
            XFITTER_COMMIT=self.alternate_commit,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tree=alternate-tree\n", result.stdout)
        self.assertIn(f"commit={self.alternate_commit}\n", result.stdout)

    def test_separate_setup_root_preserves_nested_and_sibling_trees(self):
        setup_root = self.install / "merge-master"
        setup_root.mkdir()
        (self.install / "setup.sh").rename(setup_root / "setup.sh")
        (self.install / "default-tree").rename(setup_root / "default-tree")
        (self.repo / ".env").write_text(
            f"XFITTER_ROOT={self.install}\n"
            f"XFITTER_SETUP_ROOT={setup_root}\n"
            "XFITTER_TREE=merge-master/default-tree\n"
            f"XFITTER_COMMIT={self.default_commit}\n"
        )
        for tree, commit, overrides in [
            ("merge-master/default-tree", self.default_commit, {}),
            ("alternate-tree", self.alternate_commit, {
                "XFITTER_TREE": "alternate-tree",
                "XFITTER_COMMIT": self.alternate_commit,
            }),
            ("alternate-tree", self.alternate_commit, {
                "XFITTER_TREE": str(self.install / "alternate-tree"),
                "XFITTER_COMMIT": self.alternate_commit,
            }),
        ]:
            with self.subTest(overrides=overrides):
                result = self._source(**overrides)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"commit={commit}\n", result.stdout)
                self.assertIn(
                    f"binary={self.install / tree / 'bin' / 'xfitter'}\n",
                    result.stdout,
                )

    def test_missing_setup_stops_even_with_a_valid_binary_on_path(self):
        (self.install / "setup.sh").unlink()
        result = self._source(
            PATH=f"{self.install / 'default-tree' / 'bin'}:{os.environ['PATH']}",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"cannot read {self.install / 'setup.sh'}", result.stderr)
        self.assertNotIn("using xFitter tree", result.stderr)
        self.assertNotIn("directory stack empty", result.stderr)

    def test_failed_environment_scripts_stop_setup(self):
        for setup in [self.lcg_setup, self.install / "setup.sh"]:
            with self.subTest(setup=setup):
                original = setup.read_text()
                setup.write_text("return 1\n")
                try:
                    result = self._source()
                finally:
                    setup.write_text(original)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"failed to source {setup}", result.stderr)
                self.assertNotIn("using xFitter tree", result.stderr)

    def test_explicit_tree_without_commit_suppresses_default_tree_pin(self):
        result = self._source(XFITTER_TREE="alternate-tree")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tree=alternate-tree\n", result.stdout)
        self.assertIn("commit=unset\n", result.stdout)

    def test_commit_mismatch_is_rejected(self):
        result = self._source(
            XFITTER_TREE="alternate-tree",
            XFITTER_COMMIT="0" * 40,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("xFitter commit mismatch", result.stderr)

    def test_tracked_changes_are_rejected_for_a_pinned_tree(self):
        (self.install / "alternate-tree" / "tracked.txt").write_text("dirty\n")
        result = self._source(
            XFITTER_TREE="alternate-tree",
            XFITTER_COMMIT=self.alternate_commit,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("has tracked changes", result.stderr)


if __name__ == "__main__":
    unittest.main()
