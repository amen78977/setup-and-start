import argparse
import contextlib
import hashlib
import importlib.util
import json
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("quality_router", ROOT / "skills/setup-and-start/scripts/router.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class QualityGateTests(unittest.TestCase):
    def test_all_skipped_unittest_fails(self):
        result = router.quality.check_outcome(["python", "-m", "unittest"], 0,
                                             "Ran 2 tests in 0.1s\nOK (skipped=2)")
        self.assertFalse(result["pass"])
        self.assertEqual(result["executed"], 0)

    def test_partially_skipped_suite_executes_real_tests(self):
        result = router.quality.check_outcome(["python", "-m", "unittest"], 0,
                                             "Ran 3 tests in 0.1s\nOK (skipped=2)")
        self.assertTrue(result["pass"])
        self.assertEqual(result["executed"], 1)

    def test_expected_failures_are_distinct_from_success_and_skips(self):
        result = router.quality.check_outcome(["python", "-m", "unittest"], 0,
                  "Ran 2 tests in 0.1s\nOK (expected failures=2)")
        self.assertFalse(result["pass"])
        self.assertEqual(result["executed"], 2)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["expected_failures"], 2)

    def test_pytest_only_skipped_or_xfailed_is_not_pass(self):
        for output in ("2 skipped in 0.1s", "3 xfailed in 0.1s", "no tests ran", "OK"):
            self.assertFalse(router.quality.check_outcome(["pytest", "-q"], 0, output)["pass"])

    def test_pytest_pass_count(self):
        self.assertEqual(router.quality.check_outcome(["python", "-m", "pytest"], 0,
                        "2 passed, 3 skipped in 0.1s")["executed"], 2)

    def test_npm_test_script_cannot_pass_with_only_skips(self):
        self.assertFalse(router.quality.check_outcome(["npm", "run", "test"], 0,
                         "Tests: 2 skipped, 2 total")["pass"])
        self.assertTrue(router.quality.check_outcome(["npm", "run", "test"], 0,
                         "Tests: 1 passed, 2 skipped, 3 total")["pass"])

    def test_failure_diagnosis_distinguishes_external_blockers(self):
        for code, message, kind in ((124, "", "timeout"),
                                   (1, "ModuleNotFoundError", "environment"),
                                   (1, "insufficient credits", "access")):
            result = router.quality.diagnose(code, message)
            self.assertEqual(result["kind"], kind)
            self.assertFalse(result["escalate"])
            self.assertFalse(result["retry"])
        self.assertTrue(router.quality.diagnose(1, "AssertionError")["escalate"])

    def test_non_git_includes_deep_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            source = project / "src/feature/nested/critical.py"
            source.parent.mkdir(parents=True)
            source.write_text("def critical(): return True\n")
            baseline = router.evidence.collect(project)["file_hashes"]
            source.write_text("def critical(): return False\n")
            observed = router.evidence.collect(project, source_baseline=baseline)
            self.assertTrue(observed["available"])
            self.assertIn("src/feature/nested/critical.py", observed["changed"])
            self.assertIn("return False", observed["patch"])

    def test_non_git_budget_overflow_is_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for i in range(2001):
                (root / f"file{i}.py").touch()
            result = router.evidence.collect(root)
            self.assertFalse(result["available"])
            self.assertFalse(result["scan_complete"])

    def test_non_git_secret_path_blocks_without_disclosure(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            (project / ".env").write_text("PRIVATE_SENTINEL")
            result = router.evidence.collect(project)
            self.assertFalse(result["available"])
            self.assertNotIn("PRIVATE_SENTINEL", str(result))

    def run_flow(self, project, **options):
        args = argparse.Namespace(project=str(project), task="Implement API helper",
            agent="auto", reviewer="auto", attempts=2, timeout=40, max_skills=3,
            check=["python check.py"], execute=True)
        for name, value in options.items():
            setattr(args, name, value)
        calls = []

        def execute(cmd, cwd, timeout):
            calls.append(cmd[0])
            if cmd[0] == "codex":
                if options.get("builder_error"):
                    return subprocess.CompletedProcess(cmd, 1, "", options["builder_error"])
                (project / "app.py").write_text("def add(a,b): return a+b\n")
                return subprocess.CompletedProcess(cmd, 0, "done", "")
            if cmd[0] == "python":
                return subprocess.CompletedProcess(cmd, 0, options.get("test_output", "OK"), "")
            return subprocess.CompletedProcess(cmd, 0, '{"approved":true,"issues":[]}', "")

        with patch.object(router, "choose_agent", side_effect=["codex", "claude"]), \
             patch.object(router, "execute", side_effect=execute):
            code = router.run(args)
        state = json.loads((project / ".setup-start/state.json").read_text())
        return code, calls, state

    def test_runner_does_not_verify_all_skipped(self):
        with tempfile.TemporaryDirectory() as folder:
            code, calls, state = self.run_flow(Path(folder), check=["python -m unittest"],
                test_output="Ran 1 test in 0.1s\nOK (skipped=1)")
            self.assertNotEqual(code, 0)
            self.assertNotIn("claude", calls)
            self.assertEqual(state["status"], "acceptance_incomplete")
            self.assertEqual(state["attempts"], 1)

    def test_environment_failure_does_not_repeat_paid_builder(self):
        with tempfile.TemporaryDirectory() as folder:
            code, calls, state = self.run_flow(Path(folder), builder_error="ModuleNotFoundError: missing package")
            self.assertNotEqual(code, 0)
            self.assertEqual(calls, ["codex"])
            self.assertEqual(state["failure_diagnosis"]["kind"], "environment")

    def test_ui_task_without_inspection_cannot_be_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            code, calls, state = self.run_flow(Path(folder), task="Build responsive React UI")
            self.assertNotEqual(code, 0)
            self.assertNotIn("claude", calls)
            self.assertFalse(state["acceptance"]["ui"]["pass"])

    def test_ui_runtime_capture_and_inspection_complete_acceptance(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            # Runtime and review files belong to local ignored state, not source.
            state_dir = project / ".setup-start"
            state_dir.mkdir()
            (state_dir / "runtime.json").write_text('{"ui_url":"http://127.0.0.1:3000"}')

            def capture(url, output):
                self.assertEqual(url, "http://127.0.0.1:3000")
                output.mkdir(parents=True, exist_ok=True)
                for viewport in ("mobile", "desktop"):
                    (output / (viewport + ".png")).write_bytes(viewport.encode())
                state = json.loads((state_dir / "state.json").read_text())
                source = router.evidence.collect(project, source_baseline=state["initial_file_sha256"])
                doc = {"approved": True, "issues": [], "reviewer": "vision-inspector",
                       "source_sha256": source["sha256"], "checks": {
                           key: "Actual journey inspected and expected behavior observed."
                           for key in ("visual", "keyboard", "responsive", "states")},
                       "screenshots": {key: hashlib.sha256(key.encode()).hexdigest()
                                       for key in ("mobile", "desktop")}}
                (state_dir / "ui-review.json").write_text(json.dumps(doc))
                return {"pass": True, "viewports": {
                    key: {"assessment": {"pass": True, "issues": []}}
                    for key in ("mobile", "desktop")}}

            with patch.object(router.browser_audit, "capture", side_effect=capture):
                code, calls, state = self.run_flow(project, task="Build responsive React UI")
            self.assertEqual(code, 0)
            self.assertIn("claude", calls)
            self.assertTrue(state["acceptance"]["ui"]["pass"])

    def test_unknown_provider_identity_is_reported_as_unknown(self):
        with tempfile.TemporaryDirectory() as folder:
            _, _, state = self.run_flow(Path(folder))
            self.assertTrue(state["review_independence"]["different_cli"])
            self.assertIsNone(state["review_independence"]["different_provider"])

    def test_known_distinct_provider_is_preferred_over_cheaper_same_provider(self):
        with tempfile.TemporaryDirectory() as folder:
            policy = Path(folder) / "models.json"
            policy.write_text(json.dumps({"models": [
                {"agent": "opencode", "provider": "provider-a", "name": "build", "strength": 3,
                 "roles": ["build"], "input_per_million": 1, "output_per_million": 1},
                {"agent": "codex", "provider": "provider-a", "name": "same", "strength": 4,
                 "roles": ["review"], "input_per_million": .1, "output_per_million": .1},
                {"agent": "claude", "provider": "provider-b", "name": "distinct", "strength": 4,
                 "roles": ["review"], "input_per_million": 2, "output_per_million": 2}]}))
            args = argparse.Namespace(project=folder, task="Implement API helper", agent="auto",
                reviewer="auto", attempts=1, timeout=40, max_skills=3, check=[], execute=False,
                model_policy=str(policy), mode="economy")
            output = io.StringIO()
            with patch.object(router.shutil, "which", return_value="installed"), \
                 patch.object(router, "choose_agent", side_effect=["opencode", "codex"]), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(router.run(args), 0)
            self.assertEqual(json.loads(output.getvalue())["review_model"]["model"], "distinct")

    def test_ui_inspection_is_bound_to_source_and_screenshots(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for viewport in ("mobile", "desktop"):
                (root / (viewport + ".png")).write_bytes(viewport.encode())
            doc = {"approved": True, "issues": [], "reviewer": "vision-reviewer",
                   "source_sha256": "source", "checks": {
                       key: "Inspected concrete journey and observed expected behavior."
                       for key in ("visual", "keyboard", "responsive", "states")},
                   "screenshots": {key: hashlib.sha256(key.encode()).hexdigest()
                                   for key in ("mobile", "desktop")}}
            path = root / "inspection.json"
            path.write_text(json.dumps(doc))
            self.assertTrue(router.quality.ui_acceptance(path, root, "source")["pass"])
            self.assertFalse(router.quality.ui_acceptance(path, root, "different source")["pass"])
            (root / "mobile.png").write_bytes(b"changed screenshot")
            self.assertFalse(router.quality.ui_acceptance(path, root, "source")["pass"])

    def test_invalid_discovery_is_not_repeated_on_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            inventory = project / "models.json"
            inventory.write_text(json.dumps({"models": [
                {"agent": "codex", "name": "build", "strength": 4, "roles": ["build"],
                 "input_per_million": 2, "output_per_million": 2},
                {"agent": "claude", "name": "review", "strength": 4, "roles": ["review"]},
                {"agent": "opencode", "name": "discover", "strength": 1, "roles": ["discover"],
                 "input_per_million": .01, "output_per_million": .01}]}))
            args = argparse.Namespace(project=folder,
                task="Implement a robust backend API helper with functional tests",
                agent="auto", reviewer="auto", attempts=1, timeout=40, max_skills=3,
                check=["python check.py"], execute=True, model_policy=str(inventory))
            discovery_calls = []
            build_calls = []

            def execute(cmd, cwd, timeout):
                if cmd[0] == "opencode":
                    discovery_calls.append(cmd)
                    return subprocess.CompletedProcess(cmd, 0, "invalid advisory response", "")
                if cmd[0] == "codex":
                    build_calls.append(cmd)
                    if len(build_calls) == 1:
                        return subprocess.CompletedProcess(cmd, 1, "", "implementation failed")
                    (project / "app.py").write_text("def add(a,b): return a+b\n")
                answer = '{"approved":true,"issues":[]}' if cmd[0] == "claude" else "OK"
                return subprocess.CompletedProcess(cmd, 0, answer, "")

            with patch.object(router.shutil, "which", return_value="installed"), \
                 patch.object(router, "choose_agent", side_effect=["codex", "claude", "codex", "claude"]), \
                 patch.object(router, "execute", side_effect=execute):
                self.assertNotEqual(router.run(args), 0)
                args.resume, args.attempts = True, 2
                self.assertEqual(router.run(args), 0)
            self.assertEqual(len(discovery_calls), 1)
            state = json.loads((project / ".setup-start/state.json").read_text())
            self.assertTrue(state["discovery_attempted"])
            self.assertIsNone(state["discovery_notes"])


if __name__ == "__main__":
    unittest.main()
