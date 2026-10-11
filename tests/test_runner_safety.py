import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "setup-and-start" / "scripts" / "router.py"
spec = importlib.util.spec_from_file_location("router_safety", SCRIPT)
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


def config(project, **overrides):
    defaults = dict(project=project, task="Build a secure backend API", agent="auto",
                    reviewer="auto", max_skills=3, attempts=1, timeout=45,
                    check=["python -m unittest"], execute=False)
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class RunnerSafetyTests(unittest.TestCase):
    def test_empty_policy_is_not_silent_provider_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "models.json"
            p.write_text('{"models":[]}', encoding="utf-8")
            with self.assertRaises(ValueError):
                router.run(config(tmp, model_policy=str(p)))

    def test_nan_cap_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "models.json"
            p.write_text(json.dumps({"models": [
                {"agent": "codex", "name": "build", "strength": 5, "roles": ["build"],
                 "input_per_million": 1, "output_per_million": 2},
                {"agent": "claude", "name": "review", "strength": 5, "roles": ["review"],
                 "input_per_million": 1, "output_per_million": 2}]}), encoding="utf-8")
            with patch.object(router.shutil, "which", return_value="fake"), patch.object(
                    router, "choose_agent", return_value="codex"):
                self.assertEqual(router.run(config(tmp, model_policy=str(p),
                                        max_estimated_usd=float("nan"))), 2)

    def test_unchanged_existing_project_cannot_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print('already here')\n", encoding="utf-8")
            def fake_execute(cmd, cwd, timeout):
                answer = '{"approved":true,"issues":[]}' if cmd[0] == "claude" else "OK"
                return subprocess.CompletedProcess(cmd, 0, answer, "")
            with patch.object(router, "choose_agent", side_effect=["codex", "claude"]), patch.object(
                    router, "execute", side_effect=fake_execute):
                code = router.run(config(tmp, execute=True))
            self.assertNotEqual(code, 0)
            state = json.loads((root / ".setup-start" / "state.json").read_text())
            self.assertNotEqual(state["status"], "verified_by_configured_checks_and_reviewer")

    def test_no_explicit_checks_fails_before_paid_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(router, "choose_agent", side_effect=["codex", "claude"]), patch.object(
                    router, "execute") as execute:
                code = router.run(config(tmp, execute=True, check=[]))
                self.assertEqual(code, 2)
                execute.assert_not_called()

    def test_check_output_not_forwarded_to_external_reviewer(self):
        secret = "Bearer real-super-private-example-token-value"
        prompt = router.review_prompt("test", Path("."), "+ changed",
                                      [{"command": ["python", "-c", secret],
                                        "exit": 1, "stderr_tail": secret}])
        self.assertNotIn(secret, prompt)
        self.assertIn('"exit": 1', prompt)

    def test_mixed_pytest_style_prioritized_over_unittest(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "tests").mkdir()
            (d / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
            (d / "tests" / "test_one.py").write_text("def test_failure():\n    assert False\n",
                                                    encoding="utf-8")
            commands = router.auto_checks(d)
            self.assertEqual(commands[0][2], "pytest")


if __name__ == "__main__":
    unittest.main()
