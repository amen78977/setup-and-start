import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / "skills" / "setup-and-start" / "scripts"
spec = importlib.util.spec_from_file_location("routing_module_runtime", ROOT / "router.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)
guard = router.runtime_guard


class GuardTests(unittest.TestCase):
    def test_lock_rejects_second_run_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            with guard.exclusive_run(folder, "abc"):
                with self.assertRaises(RuntimeError):
                    with guard.exclusive_run(folder, "different"):
                        pass
            self.assertFalse((folder / "run.lock").exists())

    def test_structured_usage(self):
        output = '{"type":"turn.completed","usage":{"input_tokens":200,"output_tokens":80}}'
        self.assertEqual(guard.usage_from_output(output)["total_tokens"], 280)
        wrapped = '{"type":"event","info":{"total_token_usage":{"input_tokens":88,"output_tokens":22}}}'
        self.assertEqual(guard.usage_from_output(wrapped)["input_tokens"], 88)
        self.assertIsNone(guard.usage_from_output("300 tokens used"))

    def test_json_response_review(self):
        msg = '{"result":"{\\\"approved\\\":true,\\\"issues\\\":[]}","usage":{"input_tokens":9,"output_tokens":4}}'
        self.assertTrue(router.parse_review(msg)["approved"])
        msg2 = '{"type":"item.completed","item":{"type":"agent_message","text":"{\\\"approved\\\":false,\\\"issues\\\":[\\\"needs tests\\\"]}"}}'
        self.assertFalse(router.parse_review(msg2)["approved"])

    def test_structured_cli_flags(self):
        self.assertIn("--json", router.agent_command("codex", "hello", structured=True))
        self.assertIn("--output-format", router.agent_command("claude", "hello", structured=True))
        self.assertIn("--format", router.agent_command("opencode", "hello", structured=True))
        self.assertIn("read-only", router.agent_command("codex", "review", role="review"))
        self.assertIn("--tools", router.agent_command("claude", "review", role="review"))
        self.assertIn("--agent", router.agent_command("opencode", "review", role="review"))


if __name__ == "__main__":
    unittest.main()
