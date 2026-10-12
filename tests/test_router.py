import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "setup-and-start" / "scripts" / "router.py"
spec = importlib.util.spec_from_file_location("setup_start_router", SCRIPT)
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class RoutingTests(unittest.TestCase):
    def test_frontend_arabic_and_rtl(self):
        ids = [x["id"] for x in router.route("تصميم واجهة عربية RTL متجاوبة", "build")]
        self.assertIn("frontend", ids)
        self.assertNotIn("backend", ids)

    def test_backend_not_frontend(self):
        ids = [x["id"] for x in router.route("Build backend API and SQL database", "build")]
        self.assertIn("backend", ids)
        self.assertNotIn("frontend", ids)

    def test_phase_isolation(self):
        ids = [x["id"] for x in router.route("Test security of an API", "review")]
        self.assertIn("security", ids)
        self.assertNotIn("backend", ids)

    def test_progressive_limit(self):
        self.assertLessEqual(len(router.route("website database mobile app deploy react n8n", "auto", 2)), 2)
        with self.assertRaises(ValueError):
            router.route("hello", "auto", 100)

    def test_registry_refs_are_bundled(self):
        for pack in router.catalog():
            self.assertTrue((router.ROOT / pack["reference"]).is_file(), pack["id"])

    def test_review_strict(self):
        self.assertIsNone(router.parse_review("Looks great!"))
        self.assertIsNone(router.parse_review('{"approved":"true","issues":[]}'))
        self.assertEqual(router.parse_review('{"approved":true,"issues":[]}')["approved"], True)
        self.assertIsNone(router.parse_review('{"approved":true,"issues":[]}\n'
                                              '{"approved":false,"issues":["not safe"]}'))

    def test_model_id_validation(self):
        with patch.dict(os.environ, {"SETUP_START_CODEX_BUILD_MODEL": "x; rm -rf /"}):
            with self.assertRaises(ValueError):
                router.agent_command("codex", "task")
        with patch.dict(os.environ, {"SETUP_START_CODEX_BUILD_MODEL": "gpt-example"}):
            self.assertEqual(router.agent_command("codex", "task"), ["codex", "exec", "-m", "gpt-example", "task"])

    def test_no_shell_interpolation(self):
        self.assertEqual(router.agent_command("opencode", "Hi ; echo HACK"), ["opencode", "run", "Hi ; echo HACK"])

    def test_runner_success_requires_check_and_independent_review(self):
        with tempfile.TemporaryDirectory() as directory:
            args = __import__("argparse").Namespace(project=directory, task="Fix backend API", agent="auto", reviewer="auto",
                                                        max_skills=3, attempts=2, timeout=45, check=["python -m unittest"], execute=True)
            calls = []
            def fake_execute(cmd, cwd, timeout):
                calls.append(cmd)
                if cmd[0] == "claude":
                    return subprocess.CompletedProcess(cmd, 0, '{"approved":true,"issues":[]}', "")
                return subprocess.CompletedProcess(cmd, 0, "Ran 1 test in 0.01s\nOK", "")
            with patch.object(router, "choose_agent", side_effect=["codex", "claude"]), patch.object(router, "execute", side_effect=fake_execute), patch.object(router.evidence, "collect", side_effect=[
                {"available": False, "scan_complete": True, "reason": "No changes initially", "changed": [], "patch": ""},
                {"available": True, "reason": "Changed in build", "changed": ["src.py"],
                 "patch": "+ def feature(): pass", "sha256": "fixture"}
            ]):
                code = router.run(args)
            self.assertEqual(code, 0)
            self.assertEqual(len(calls), 3)
            state = json.loads((Path(directory) / ".setup-start" / "state.json").read_text())
            self.assertEqual(state["status"], "verified_by_configured_checks_and_reviewer")

    def test_runner_never_claims_verification_without_review(self):
        with tempfile.TemporaryDirectory() as directory:
            args = __import__("argparse").Namespace(project=directory, task="Fix bug", agent="auto", reviewer="auto",
                                                        max_skills=3, attempts=1, timeout=45, check=[], execute=True)
            with patch.object(router, "choose_agent", side_effect=["codex", None]), patch.object(router, "execute", return_value=subprocess.CompletedProcess([], 0, "", "")):
                code = router.run(args)
            self.assertEqual(code, 2)
            self.assertFalse((Path(directory) / ".setup-start" / "state.json").exists())


if __name__ == "__main__":
    unittest.main()
