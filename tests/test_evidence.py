import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / "skills" / "setup-and-start" / "scripts"
spec = importlib.util.spec_from_file_location("routing_module3", ROOT / "router.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)
evidence = router.evidence


class EvidenceTests(unittest.TestCase):
    def test_non_git_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(evidence.collect(Path(tmp))["available"])

    def test_non_git_project_source_can_be_reviewed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "src").mkdir()
            (p / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
            (p / ".env").write_text("password=NOT_FOR_REVIEW", encoding="utf-8")
            review = evidence.collect(p)
            self.assertTrue(review["available"])
            self.assertIn("src/app.py", review["changed"])
            self.assertNotIn("NOT_FOR_REVIEW", review["patch"])

    def test_diff_detected_without_env_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            def git(*cmd):
                return subprocess.run(["git", *cmd], cwd=d, capture_output=True, check=True)
            git("init", "-q")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.org")
            (d / "main.py").write_text("x = 1\n", encoding="utf-8")
            git("add", "main.py")
            git("commit", "-qm", "initial")
            (d / "main.py").write_text("x = 2\n", encoding="utf-8")
            (d / ".env").write_text("password=PRIVATE", encoding="utf-8")
            found = evidence.collect(d)
            self.assertTrue(found["available"])
            self.assertEqual(found["changed"], ["main.py"])
            self.assertNotIn("PRIVATE", found["patch"])

    def test_secrets_block_external_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=d, check=True)
            (d / "secrets.py").write_text("api_key = '123456789abcdef'\n", encoding="utf-8")
            found = evidence.collect(d)
            self.assertFalse(found["available"])
            self.assertEqual(found["patch"], "")


if __name__ == "__main__":
    unittest.main()
