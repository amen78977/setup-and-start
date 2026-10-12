"""Regression gates for complete review, context economy and real counters."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "efficiency_router", ROOT / "skills/setup-and-start/scripts/router.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class EfficiencyTests(unittest.TestCase):
    def test_large_new_source_refuses_partial_review(self):
        with tempfile.TemporaryDirectory() as folder:
            subprocess.run(["git", "init", "-q", folder], check=True)
            project = Path(folder)
            (project / "large.py").write_text("x = 1\n" * 2100)
            result = router.evidence.collect(project)
            self.assertFalse(result["available"])
            self.assertEqual(result["patch"], "")
            self.assertIn("large.py", result["reason"])

    def test_independent_turns_are_summed(self):
        events = [{"type": "turn.completed", "usage": {
            "input_tokens": i, "output_tokens": o}} for i, o in [(100, 20), (200, 30)]]
        result = router.runtime_guard.usage_from_output("\n".join(map(json.dumps, events)))
        self.assertEqual(result["total_tokens"], 350)

    def test_cumulative_counter_is_not_double_counted(self):
        events = [{"type": "turn.completed", "usage": {
            "input_tokens": 100, "output_tokens": 20}},
            {"info": {"total_token_usage": {"input_tokens": 100, "output_tokens": 20}}}]
        self.assertEqual(router.runtime_guard.usage_from_output(
            "\n".join(map(json.dumps, events)))["total_tokens"], 120)

    def test_usage_survives_long_output(self):
        output = json.dumps({"type": "turn.completed", "usage": {
            "input_tokens": 10, "output_tokens": 5}}) + "\n" + "log\n" * 200
        self.assertEqual(router.runtime_guard.usage_from_output(output)["total_tokens"], 15)

    def test_opencode_steps_sum_and_deduplicate(self):
        events = [{"type": "step_finish", "part": {"id": ident,
            "tokens": {"input": i, "output": o}}}
            for ident, i, o in [("a", 10, 5), ("a", 10, 5), ("b", 20, 5)]]
        self.assertEqual(router.runtime_guard.usage_from_output(
            "\n".join(map(json.dumps, events)))["total_tokens"], 40)

    def test_oversized_pack_does_not_block_smaller_pack(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "large.md").write_text("x" * 500)
            (root / "small.md").write_text("MANDATORY CHECK")
            selected = [{"id": "frontend", "reference": "large.md"},
                        {"id": "verification", "reference": "small.md"}]
            with patch.object(router.planner, "ROOT", root):
                result = router.planner.read_guidance(selected, 256)
            self.assertIn("MANDATORY CHECK", result)
            self.assertIn("not loaded", result)
            self.assertLessEqual(len(result), 256)

    def test_balanced_can_choose_modest_quality_premium(self):
        rows = [{"agent": "codex", "name": "cheap", "strength": 3,
                 "input_per_million": 1, "output_per_million": 1},
                {"agent": "claude", "name": "strong", "strength": 5,
                 "input_per_million": 1.2, "output_per_million": 1.2}]
        self.assertEqual(router.model_policy.recommend(rows, "API", "build", "economy")["model"], "cheap")
        self.assertEqual(router.model_policy.recommend(rows, "API", "build", "balanced")["model"], "strong")

    def test_ui_plan_has_explicit_acceptance_gate(self):
        plan = router.planner.make_plan("Build an Arabic RTL website")
        self.assertIn("ui", [gate["id"] for gate in plan["acceptance_gates"]])
        self.assertIn("ownership", plan["delegation_policy"])

    def test_same_cli_can_select_distinct_reviewer_model(self):
        rows = [{"agent": "codex", "name": "builder", "strength": 4},
                {"agent": "codex", "name": "reviewer", "strength": 4}]
        selected = router.model_policy.recommend(
            rows, "Review API", "review", exclude_model=("codex", "builder"))
        self.assertEqual(selected["model"], "reviewer")


if __name__ == "__main__":
    unittest.main()
