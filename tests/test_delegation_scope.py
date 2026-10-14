import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("scoped_router",
    ROOT / "skills/setup-and-start/scripts/router.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class DelegationScopeTests(unittest.TestCase):
    def project(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        def git(*args):
            return subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True)
        git("init", "-q")
        git("config", "user.name", "Test")
        git("config", "user.email", "test@example.org")
        (root / "src").mkdir()
        (root / "src/app.py").write_text("x = 1\n")
        (root / "other.py").write_text("y = 1\n")
        git("add", ".")
        git("commit", "-qm", "initial")
        return root, git

    def test_scope_validation_rejects_escapes_and_wildcards(self):
        for name in ("../src", "/tmp/src", "C:\\src", ".", "src/*", ".git/config", ".setup-start/state.json"):
            with self.assertRaises(ValueError):
                router.delegate.validate_scope([name])
        self.assertEqual(router.delegate.validate_scope(["src/", "src", "tests\\unit.py"]),
                         ["src", "tests/unit.py"])

    def test_contract_contains_real_checks_and_commit_ownership(self):
        contract = router.delegate.task_contract(["src"], [["python", "-m", "unittest"]])
        self.assertEqual(contract["verification_commands"], [["python", "-m", "unittest"]])
        self.assertIn("do not commit", " ".join(contract["constraints"]))

    def test_scope_detects_renames_and_committed_changes(self):
        root, git = self.project()
        baseline = git("rev-parse", "HEAD").stdout.decode().strip()
        git("mv", "src/app.py", "moved.py")
        git("commit", "-qm", "move")
        result = router.delegate.check_scope(root, ["src"], baseline)
        self.assertFalse(result["pass"])
        self.assertIn("moved.py", result["unexpected"])

    def test_file_scope_does_not_grant_sibling_prefix(self):
        root, _ = self.project()
        (root / "src/app.py.extra").write_text("unowned")
        result = router.delegate.check_scope(root, ["src/app.py"])
        self.assertFalse(result["pass"])
        self.assertEqual(result["unexpected"], ["src/app.py.extra"])

    def run_fixture(self, outside=False, check_writes=False, failed_builder=False):
        root, _ = self.project()
        args = argparse.Namespace(project=str(root), task="Implement API helper", agent="auto",
            reviewer="auto", attempts=2, timeout=40, max_skills=3, check=["python check.py"],
            execute=True, allow_path=["src"])
        calls = []
        def execute(cmd, cwd, timeout):
            calls.append(cmd[0])
            if cmd[0] == "codex":
                self.assertIn('"owned_paths": ["src"]', cmd[-1])
                self.assertIn('"verification_commands": [["python", "check.py"]]', cmd[-1])
                (root / "src/app.py").write_text("x = 2\n")
                if outside:
                    (root / "other.py").write_text("y = 2\n")
                return subprocess.CompletedProcess(cmd, 1 if failed_builder else 0, "done", "implementation failed" if failed_builder else "")
            if cmd[0] == "python" and check_writes:
                (root / "generated.json").write_text("{}")
            answer = '{"approved":true,"issues":[]}' if cmd[0] == "claude" else "OK"
            return subprocess.CompletedProcess(cmd, 0, answer, "")
        with patch.object(router, "choose_agent", side_effect=["codex", "claude"]), \
             patch.object(router, "execute", side_effect=execute):
            code = router.run(args)
        state = json.loads((root / ".setup-start/state.json").read_text())
        return root, code, calls, state

    def test_scoped_implementation_can_pass(self):
        _, code, calls, state = self.run_fixture()
        self.assertEqual(code, 0)
        self.assertEqual(calls, ["codex", "python", "claude"])
        self.assertTrue(state["ownership"]["pass"])

    def test_out_of_scope_edits_are_preserved_and_block_review(self):
        root, code, calls, state = self.run_fixture(outside=True)
        self.assertNotEqual(code, 0)
        self.assertEqual(calls, ["codex"])
        self.assertEqual(state["status"], "scope_violation")
        self.assertEqual(state["ownership"]["unexpected"], ["other.py"])
        self.assertEqual((root / "other.py").read_text(), "y = 2\n")

    def test_failed_builder_scope_violation_does_not_trigger_retry(self):
        _, code, calls, state = self.run_fixture(outside=True, failed_builder=True)
        self.assertNotEqual(code, 0)
        self.assertEqual(calls, ["codex"])
        self.assertEqual(state["status"], "scope_violation")

    def test_verification_side_effects_are_also_checked(self):
        _, code, calls, state = self.run_fixture(check_writes=True)
        self.assertNotEqual(code, 0)
        self.assertNotIn("claude", calls)
        self.assertEqual(state["ownership"]["unexpected"], ["generated.json"])

    def test_non_git_changed_paths_use_baseline_hashes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "app.py").write_text("x = 1\n")
            baseline = router.evidence.collect(root)["file_hashes"]
            (root / "app.py").write_text("x = 2\n")
            self.assertTrue(router.delegate.check_scope(root, ["app.py"], source_baseline=baseline)["pass"])
            (root / "other.py").write_text("y = 2\n")
            self.assertFalse(router.delegate.check_scope(root, ["app.py"], source_baseline=baseline)["pass"])

    def test_resume_cannot_silently_expand_ownership(self):
        root, _, _, _ = self.run_fixture(outside=True)
        args = argparse.Namespace(project=str(root), task="Implement API helper", agent="auto",
            reviewer="auto", attempts=2, timeout=40, max_skills=3, check=["python check.py"],
            execute=True, allow_path=["src", "other.py"], resume=True)
        with patch.object(router, "choose_agent", side_effect=["codex", "claude"]), \
             patch.object(router, "execute") as execute:
            self.assertEqual(router.run(args), 2)
            execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
