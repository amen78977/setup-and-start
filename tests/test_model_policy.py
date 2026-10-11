from pathlib import Path
import importlib.util
import json
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / "skills" / "setup-and-start" / "scripts"
spec = importlib.util.spec_from_file_location("routing_module2", ROOT / "router.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)
policy = router.model_policy


class ModelPolicyTests(unittest.TestCase):
    def test_capital_does_not_contain_api_task(self):
        self.assertEqual(policy.complexity("capital investment", "build"), 2)
    def test_minimum_quality_and_price(self):
        rows = [
            {"agent": "codex", "name": "cheap", "strength": 2,
             "input_per_million": 0.1, "output_per_million": 0.5},
            {"agent": "claude", "name": "medium", "strength": 4,
             "input_per_million": 1, "output_per_million": 3},
            {"agent": "opencode", "name": "premium", "strength": 5,
             "input_per_million": 10, "output_per_million": 30},
        ]
        pick = policy.recommend(rows, "security architecture migration", "build", "economy")
        self.assertEqual(pick["model"], "medium")
        pick = policy.recommend(rows, "simple greeting", "build", "quality")
        self.assertEqual(pick["model"], "premium")

    def test_unknown_prices_never_count_as_zero(self):
        rows = [
            {"agent": "codex", "name": "unknown", "strength": 5},
            {"agent": "claude", "name": "priced", "strength": 5,
             "input_per_million": 8, "output_per_million": 20},
        ]
        self.assertEqual(policy.recommend(rows, "complex API", "build")["model"], "priced")

    def test_invalid_identifiers_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "models.json"
            file.write_text(json.dumps({"models":[{"agent":"codex","name":"x;cmd",
                "strength":5}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                policy.load_policy(file)

    def test_different_provider_reviewer(self):
        rows = [{"agent": "codex", "name": "same", "strength":5},
                {"agent": "claude", "name": "other", "strength":5}]
        chosen = policy.recommend(rows, "review API", "review", exclude="codex")
        self.assertEqual(chosen["agent"], "claude")


if __name__ == "__main__":
    unittest.main()
