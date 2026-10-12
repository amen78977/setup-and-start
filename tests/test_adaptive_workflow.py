import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/setup-and-start/scripts"
spec = importlib.util.spec_from_file_location("adaptive_router", SCRIPTS / "router.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class AdaptiveWorkflowTests(unittest.TestCase):
    def models(self):
        return [dict(agent="codex", name="initial", strength=3, roles=["build"],
                     input_per_million=1, output_per_million=1),
                dict(agent="codex", name="strong", strength=4, roles=["build"],
                     input_per_million=2, output_per_million=2),
                dict(agent="claude", name="review", strength=4, roles=["review"],
                     input_per_million=1, output_per_million=1)]

    def run_fixture(self, **overrides):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        project = Path(folder.name)
        policy = project / "models.json"
        policy.write_text(json.dumps({"models": self.models()}))
        args = argparse.Namespace(project=str(project), task="Implement API helper",
            agent="auto", reviewer="auto", attempts=2, timeout=40, max_skills=3,
            check=["python check.py"], execute=True, model_policy=str(policy),
            no_delegation=True, mode="economy")
        for key, value in overrides.items():
            setattr(args, key, value)
        builds = []

        def command(agent, prompt, role="build", override_model=None, structured=False):
            return [agent, role, override_model or "default"]

        def execute(cmd, cwd, timeout):
            if cmd[0] == "python":
                if getattr(args, "failure_in_checks", False) and len(builds) == 1:
                    return subprocess.CompletedProcess(cmd, 1, "", "functional acceptance failed")
                return subprocess.CompletedProcess(cmd, 0, "OK", "")
            if cmd[1] == "build":
                builds.append(cmd[2])
                if len(builds) == 1 and not getattr(args, "failure_in_checks", False):
                    return subprocess.CompletedProcess(cmd, 1, "", "implementation failed")
                (project / "app.py").write_text("def add(a, b): return a + b\n")
                return subprocess.CompletedProcess(cmd, 0, "done", "")
            return subprocess.CompletedProcess(cmd, 0, '{"approved":true,"issues":[]}', "")

        with patch.object(router.shutil, "which", return_value="installed"), \
             patch.object(router, "choose_agent", side_effect=["codex", "claude"]), \
             patch.object(router, "agent_command", side_effect=command), \
             patch.object(router, "execute", side_effect=execute):
            code = router.run(args)
        state_path = project / ".setup-start/state.json"
        state = json.loads(state_path.read_text()) if state_path.exists() else {}
        return code, builds, state

    def test_failure_upgrades_and_records_transition(self):
        code, builds, state = self.run_fixture()
        self.assertEqual(code, 0)
        self.assertEqual(builds, ["initial", "strong"])
        self.assertEqual(state["model_transitions"][0]["to"], "strong")

    def test_no_escalation_preserves_model(self):
        code, builds, state = self.run_fixture(no_escalation=True)
        self.assertEqual(code, 0)
        self.assertEqual(builds, ["initial", "initial"])
        self.assertEqual(state["model_transitions"], [])

    def test_failing_checks_do_not_spend_reviewer_turn(self):
        code, builds, state = self.run_fixture(failure_in_checks=True)
        self.assertEqual(code, 0)
        self.assertEqual(builds, ["initial", "strong"])
        self.assertEqual([row["role"] for row in state["telemetry"]],
                         ["build", "build", "review"])

    def test_forecast_cap_covers_upgrade_before_execution(self):
        # Original two-attempt plan costs .052; upgrade envelope costs .078.
        code, builds, _ = self.run_fixture(max_estimated_usd=.06)
        self.assertEqual(code, 2)
        self.assertEqual(builds, [])

    def test_upgrade_never_selects_reviewer(self):
        rows = self.models()
        current = router.model_policy.recommend(rows, "API", "build", "economy")
        reviewer = dict(agent="codex", model="strong")
        self.assertEqual(router.model_policy.repair_candidates(rows, current, reviewer,
                                                              "API", "economy"), [])

    def test_authentication_reserves_security_and_verification(self):
        for stage in ("test", "review"):
            ids = [pack["id"] for pack in router.route("Implement authentication API", stage, 2)]
            self.assertIn("security", ids)
            self.assertIn("verification", ids)

    def test_unsupported_file_blocks_incomplete_review(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            subprocess.run(["git", "init", "-q", folder], check=True)
            (project / "app.py").write_text("x = 1\n")
            (project / "image.png").write_bytes(b"image content")
            result = router.evidence.collect(project)
            self.assertFalse(result["available"])
            self.assertIn("image.png", result["reason"])

    def test_binary_content_with_source_suffix_is_not_reviewable(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            subprocess.run(["git", "init", "-q", folder], check=True)
            (project / "app.py").write_bytes(b"looks like source\0binary")
            result = router.evidence.collect(project)
            self.assertFalse(result["available"])
            self.assertIn("Non-text", result["reason"])

    def test_symlink_cannot_substitute_review_content(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            subprocess.run(["git", "init", "-q", folder], check=True)
            (project / "app.py").write_text("x = 1\n")
            try:
                (project / "link.py").symlink_to(project / "app.py")
            except OSError:
                self.skipTest("Symlink creation unavailable on this platform")
            result = router.evidence.collect(project)
            self.assertFalse(result["available"])
            self.assertIn("Symlink", result["reason"])


if __name__ == "__main__":
    unittest.main()
