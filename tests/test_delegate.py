import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "skills" / "setup-and-start" / "scripts"
spec = importlib.util.spec_from_file_location("routing_module_delegate", ROOT / "router.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)
d = router.delegate


class DelegationTests(unittest.TestCase):
    def test_delegates_cheap_subtask_only_when_justified(self):
        rows = [
            {"agent": "claude", "name": "strong", "strength": 5, "roles": ["build"],
             "input_per_million": 10, "output_per_million": 40},
            {"agent": "codex", "name": "small", "strength": 2, "roles": ["discover"],
             "input_per_million": 0.1, "output_per_million": 0.3},
        ]
        main = router.model_policy.recommend(rows, "Build a secure backend with auth, migrations, and tests",
                                              "build", "balanced")
        self.assertTrue(d.discovery_option(rows, "Build a secure backend with auth, migrations, and tests",
                                            main, "balanced", {"codex", "claude"})["delegate"])
        self.assertFalse(d.discovery_option(rows, "fix typo", main, "balanced",
                                             {"codex", "claude"})["delegate"])

    def test_invalid_or_long_output_rejected(self):
        valid = {"files": ["src/api.py"], "risks": ["Auth"], "acceptance": ["Tests pass"]}
        self.assertEqual(d.parse(json.dumps(valid)), valid)
        self.assertIsNone(d.parse(json.dumps({**valid, "run": ["delete database"]})))
        self.assertIsNone(d.parse("x" * 16001))
        event = {"item": {"text": json.dumps(valid)}}
        self.assertEqual(d.parse(json.dumps(event)), valid)


if __name__ == "__main__":
    unittest.main()
