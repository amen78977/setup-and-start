"""Execute the workflow against tiny local fake CLIs, never paid providers.

These tests exercise subprocess execution, Git evidence, checks, retries and
JSON review instead of replacing the entire orchestration with mocks.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import importlib.util

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "setup-and-start" / "scripts"
spec = importlib.util.spec_from_file_location("release_runner", SCRIPTS / "router.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)

FAKE_AGENT = '''import pathlib, sys
role, prompt = sys.argv[1:3]
if role == "build":
    path = pathlib.Path("app.py")
    path.write_text("def add(a, b):\\n    return a + b\\n", encoding="utf-8")
    print("build complete")
elif role == "review":
    assert "changed source" in prompt.lower()
    print('{"approved": true, "issues": []}')
else:
    raise SystemExit(2)
'''


class WorkflowIntegrationTest(unittest.TestCase):
    def test_real_subprocess_repair_escalation(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            fake = project / "fake_cli.py"
            fake.write_text(
                "import sys\nmodel = sys.argv.pop(1)\n"
                "if model == 'initial':\n"
                "    print('Needs stronger model', file=sys.stderr)\n"
                "    raise SystemExit(1)\n" + FAKE_AGENT)
            check = project / "check.py"
            check.write_text("import app\nassert app.add(2, 3) == 5\n")
            policy = project / "models.json"
            policy.write_text(json.dumps({"models": [
                {"agent": "codex", "name": "initial", "strength": 3, "roles": ["build"],
                 "input_per_million": 1, "output_per_million": 1},
                {"agent": "codex", "name": "strong", "strength": 4, "roles": ["build"],
                 "input_per_million": 2, "output_per_million": 2},
                {"agent": "claude", "name": "review", "strength": 4, "roles": ["review"]}]}))
            args = argparse.Namespace(project=directory, task="Implement API helper",
                agent="auto", reviewer="auto", attempts=2, timeout=40, max_skills=3,
                check=[f'"{sys.executable}" "{check}"'], execute=True,
                model_policy=str(policy), mode="economy", no_delegation=True)

            def command(agent, prompt, role="build", override_model=None, structured=False):
                return [sys.executable, str(fake), override_model, role, prompt]

            with patch.object(router, "choose_agent", side_effect=["codex", "claude"]), \
                 patch.object(router.shutil, "which", return_value="installed"), \
                 patch.object(router, "agent_command", side_effect=command):
                self.assertEqual(router.run(args), 0)
            state = json.loads((project / ".setup-start/state.json").read_text())
            self.assertEqual(state["build_model"]["model"], "strong")
            self.assertEqual(state["attempts"], 2)
            self.assertEqual([row["role"] for row in state["telemetry"]],
                             ["build", "build", "review"])

    def test_single_cli_distinct_model_review(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            fake = project / "fake_cli.py"
            fake.write_text(FAKE_AGENT, encoding="utf-8")
            check = project / "check.py"
            check.write_text("import app\nassert app.add(2, 3) == 5\n")
            policy = project / "models.json"
            policy.write_text(json.dumps({"models": [
                {"agent": "codex", "name": "build-model", "strength": 4, "roles": ["build"]},
                {"agent": "codex", "name": "review-model", "strength": 4, "roles": ["review"]}]}))
            args = argparse.Namespace(project=directory, task="Implement API helper",
                agent="auto", reviewer="auto", attempts=1, timeout=40, max_skills=3,
                check=[f'"{sys.executable}" "{check}"'], execute=True, model_policy=str(policy))
            models = []

            def command(agent, prompt, role="build", override_model=None, structured=False):
                models.append((role, override_model))
                return [sys.executable, str(fake), role, prompt]

            with patch.object(router, "choose_agent", side_effect=["codex", None]), \
                 patch.object(router.shutil, "which", side_effect=lambda name: "/fake/codex" if name == "codex" else None), \
                 patch.object(router, "agent_command", side_effect=command):
                self.assertEqual(router.run(args), 0)
            self.assertEqual(models, [("build", "build-model"), ("review", "review-model")])

    def test_resume_preserves_repair_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            fake = project / "fake_cli.py"
            fake.write_text(FAKE_AGENT, encoding="utf-8")
            check = project / "check.py"
            check.write_text("raise AssertionError('acceptance sentinel')\n")
            args = argparse.Namespace(project=directory, task="Implement API helper",
                agent="auto", reviewer="auto", attempts=1, timeout=40, max_skills=3,
                check=[f'"{sys.executable}" "{check}"'], execute=True)
            prompts = []

            def command(agent, prompt, role="build", override_model=None, structured=False):
                if role == "build":
                    prompts.append(prompt)
                return [sys.executable, str(fake), role, prompt]

            with patch.object(router, "choose_agent", side_effect=["codex", "claude"]), \
                 patch.object(router, "agent_command", side_effect=command):
                self.assertEqual(router.run(args), 1)
            args.resume, args.attempts = True, 2
            check.write_text("import app\nassert app.add(2, 3) == 5\n")
            with patch.object(router, "choose_agent", side_effect=["codex", "claude"]), \
                 patch.object(router, "agent_command", side_effect=command):
                self.assertEqual(router.run(args), 0)
            self.assertIn("acceptance sentinel", prompts[1])

    def test_build_check_independent_review_happy_path(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            fake = project / "fake_cli.py"
            fake.write_text(FAKE_AGENT, encoding="utf-8")
            # Check a real generated function using actual Python interpreter.
            check = project / "check.py"
            check.write_text(
                "import app\nassert app.add(2, 3) == 5\nprint('OK')\n",
                encoding="utf-8")
            args = argparse.Namespace(
                project=directory, task="Implement a tiny API helper", agent="auto",
                reviewer="auto", attempts=2, timeout=40, max_skills=3,
                check=[f'"{sys.executable}" "{check}"'], execute=True)

            def command(agent, prompt, role="build", override_model=None, structured=False):
                return [sys.executable, str(fake), role, prompt]

            with patch.object(router, "choose_agent", side_effect=["codex", "claude"]), \
                 patch.object(router, "agent_command", side_effect=command):
                result = router.run(args)

            self.assertEqual(result, 0)
            state = json.loads((project / ".setup-start" / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "verified_by_configured_checks_and_reviewer")
            self.assertEqual(state["attempts"], 1)
            self.assertEqual(state["review"]["issues"], [])
            self.assertEqual(len(state["telemetry"]), 2)
            self.assertTrue((project / "app.py").is_file())

    def test_missing_reviewer_does_not_trigger_repeated_paid_builds(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            fake = project / "fake_cli.py"
            fake.write_text(FAKE_AGENT, encoding="utf-8")
            check = project / "check.py"
            check.write_text("import app\nassert app.add(1, 2) == 3\n", encoding="utf-8")
            args = argparse.Namespace(
                project=directory, task="Implement a tiny API helper", agent="auto",
                reviewer="auto", attempts=3, timeout=40, max_skills=3,
                check=[f'"{sys.executable}" "{check}"'], execute=True)

            def command(agent, prompt, role="build", override_model=None, structured=False):
                return [sys.executable, str(fake), role, prompt]

            with patch.object(router, "choose_agent", side_effect=["codex", None]), \
                 patch.object(router, "agent_command", side_effect=command):
                result = router.run(args)

            state = json.loads((project / ".setup-start" / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertEqual(state["status"], "tests_passed_review_unavailable")
            self.assertEqual(state["attempts"], 1)
            self.assertEqual(len(state["telemetry"]), 1)

    def test_unittest_zero_tests_cannot_be_reported_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            fake = project / "fake_cli.py"
            fake.write_text(FAKE_AGENT, encoding="utf-8")
            args = argparse.Namespace(
                project=directory, task="Implement an API feature", agent="auto",
                reviewer="auto", attempts=1, timeout=40, max_skills=3,
                check=[f'"{sys.executable}" -m unittest discover -s .'], execute=True)

            def command(agent, prompt, role="build", override_model=None, structured=False):
                return [sys.executable, str(fake), role, prompt]

            with patch.object(router, "choose_agent", side_effect=["codex", "claude"]), \
                 patch.object(router, "agent_command", side_effect=command):
                result = router.run(args)
            state = json.loads((project / ".setup-start" / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertEqual(state["status"], "acceptance_incomplete")
            self.assertTrue(any("Ran 0 tests" in row["stderr_tail"] for row in state["checks"]))


if __name__ == "__main__":
    unittest.main()
