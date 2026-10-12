"""Reproduce findings from adversarial review before accepting repairs."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("review_regression_router",
    ROOT / "skills/setup-and-start/scripts/router.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class ReviewRegressionTests(unittest.TestCase):
    def project(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        def git(*args):
            return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
        git("init", "-q")
        git("config", "user.name", "Test")
        git("config", "user.email", "test@example.org")
        for name in ("build/core.py", "dist/helper.py", "main.py"):
            source = root / name
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("x = 1\n")
        git("add", ".")
        git("commit", "-qm", "initial")
        return root, git

    def test_tracked_source_in_cache_names_is_included(self):
        root, _ = self.project()
        for name in ("build/core.py", "dist/helper.py", "main.py"):
            (root / name).write_text("x = 2\n")
        result = router.evidence.collect(root)
        self.assertTrue(result["available"])
        self.assertEqual(result["changed"], ["build/core.py", "dist/helper.py", "main.py"])
        self.assertIn("build/core.py", result["patch"])
        self.assertIn("dist/helper.py", result["patch"])

    def test_committed_cache_changes_and_deletions_are_included(self):
        root, git = self.project()
        baseline = git("rev-parse", "HEAD").stdout.decode().strip()
        (root / "build/core.py").write_text("x = 2\n")
        (root / "dist/helper.py").unlink()
        git("add", ".")
        git("commit", "-qm", "update")
        result = router.evidence.collect(root, baseline=baseline)
        self.assertTrue(result["available"])
        self.assertEqual(result["changed"], ["build/core.py", "dist/helper.py"])
        self.assertIn("deleted file mode", result["patch"])

    def test_untracked_generated_outputs_stay_excluded(self):
        root, _ = self.project()
        (root / "build/generated.py").write_text("x = 99\n")
        (root / "main.py").write_text("x = 2\n")
        result = router.evidence.collect(root)
        self.assertEqual(result["changed"], ["main.py"])

    def test_tracked_binary_in_cache_folder_blocks_partial_review(self):
        root, git = self.project()
        (root / "build/data.bin").write_bytes(b"binary\0content")
        git("add", ".")
        git("commit", "-qm", "asset")
        (root / "build/data.bin").write_bytes(b"changed\0content")
        (root / "main.py").write_text("x = 2\n")
        result = router.evidence.collect(root)
        self.assertFalse(result["available"])

    def test_test_assertions_do_not_become_access_blockers(self):
        for message in ("AssertionError: expected unauthorized response, received 200",
                        "assert status == 403 # permission denied expected",
                        "AssertionError: expected connection refused, got success"):
            for phase in ("build", "check"):
                result = router.quality.diagnose(1, message, phase=phase)
                self.assertEqual(result["kind"], "implementation")
                self.assertTrue(result["escalate"])

    def test_actual_external_failures_remain_blockers(self):
        for phase in ("build", "check"):
            for message, kind in (("authentication failed", "access"),
                                  ("connection refused", "environment"),
                                  ("ModuleNotFoundError", "environment")):
                self.assertEqual(router.quality.diagnose(1, message, phase)["kind"], kind)

    def test_versioned_and_wrapped_test_reports_cannot_pass_all_skipped(self):
        for command in (["pytest-3", "-q"], ["/usr/bin/pytest3.12.exe"], ["./run-tests.sh"]):
            result = router.quality.check_outcome(command, 0, "2 skipped in 0.1s")
            self.assertFalse(result["pass"])
            self.assertEqual(result["executed"], 0)

    def test_failed_summary_cannot_be_hidden_by_zero_exit(self):
        result = router.quality.check_outcome(["pytest-3"], 0, "1 passed, 1 failed in 0.1s")
        self.assertFalse(result["pass"])

    def test_ansi_test_summary_is_understood(self):
        result = router.quality.check_outcome(["custom-wrapper"], 0,
                                             "\x1b[32m2 passed\x1b[0m in 0.1s")
        self.assertTrue(result["pass"])
        self.assertEqual(result["passed"], 2)


if __name__ == "__main__":
    unittest.main()
