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
            review = evidence.collect(p)
            self.assertTrue(review["available"])
            self.assertIn("src/app.py", review["changed"])
            self.assertTrue(review["scan_complete"])

    def test_non_git_review_only_includes_new_or_modified_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "src").mkdir()
            (d / "src" / "old.py").write_text("old = 1\n", encoding="utf-8")
            baseline = evidence.collect(d)["file_hashes"]
            (d / "src" / "new.py").write_text("fresh = 2\n", encoding="utf-8")
            result = evidence.collect(d, source_baseline=baseline)
            self.assertTrue(result["available"])
            self.assertEqual(result["changed"], ["src/new.py"])
            self.assertNotIn("old = 1", result["patch"])

    def test_non_git_deleted_source_blocks_remote_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "src").mkdir()
            path = project / "src" / "core.py"
            path.write_text("def old(): return 1\n", encoding="utf-8")
            base = evidence.collect(project)["file_hashes"]
            path.unlink()
            (project / "src" / "new.py").write_text("def new(): return 2\n", encoding="utf-8")
            changed = evidence.collect(project, source_baseline=base)
            self.assertFalse(changed["available"])
            self.assertIn("deletion", changed["reason"])

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
            (d / ".gitignore").write_text(".env\n", encoding="utf-8")
            (d / ".env").write_text("password=PRIVATE", encoding="utf-8")
            found = evidence.collect(d)
            self.assertTrue(found["available"])
            self.assertEqual(found["changed"], [".gitignore", "main.py"])
            self.assertNotIn("PRIVATE", found["patch"])

    def test_secrets_block_external_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=d, check=True)
            (d / "secrets.py").write_text("api_key = '123456789abcdef'\n", encoding="utf-8")
            found = evidence.collect(d)
            self.assertFalse(found["available"])
            self.assertEqual(found["patch"], "")

    def test_json_bearer_and_private_keys_block_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=d, check=True)
            (d / "src").mkdir()
            for name, content in (
                ("auth.json", '{"password": "secret-value-123456"}'),
                ("header.py", 'header = "Authorization: Bearer aabbccddee112233445566"'),
                ("pem.py", '-----BEGIN PRIVATE KEY-----\nAAAA'),
            ):
                (d / "src" / name).write_text(content, encoding="utf-8")
                self.assertFalse(evidence.collect(d)["available"])
                (d / "src" / name).unlink()

    def test_untracked_source_in_nested_directory_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=d, check=True)
            (d / "src").mkdir()
            (d / "src" / "new.py").write_text("x = 5\n", encoding="utf-8")
            found = evidence.collect(d)
            self.assertTrue(found["available"])
            self.assertIn("src/new.py", found["changed"])

    def test_committed_changes_since_baseline_still_reviewable(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            def git(*cmd):
                return subprocess.run(["git", *cmd], cwd=d, capture_output=True,
                                      text=True, check=True).stdout.strip()
            git("init", "-q")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.org")
            (d / "main.py").write_text("x = 1\n", encoding="utf-8")
            git("add", "main.py")
            git("commit", "-qm", "initial")
            baseline = git("rev-parse", "HEAD")
            (d / "main.py").write_text("x = 2\n", encoding="utf-8")
            git("add", "main.py")
            git("commit", "-qm", "builder committed")
            found = evidence.collect(d, baseline=baseline)
            self.assertTrue(found["available"])
            self.assertIn("+x = 2", found["patch"])
            with self.assertRaises(ValueError):
                evidence.collect(d, baseline="HEAD; rm -rf .")

    def test_git_unicode_spaced_and_flutter_files_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            subprocess.run(["git", "init", "-q"], cwd=p, check=True)
            (p / "واجهة جميلة.vue").write_text("<template>Test</template>", encoding="utf-8")
            (p / "screen.dart").write_text("void main() {}", encoding="utf-8")
            info = evidence.collect(p)
            self.assertTrue(info["available"], info)
            self.assertIn("واجهة جميلة.vue", info["changed"])
            self.assertIn("screen.dart", info["changed"])

    def test_more_than_100_changed_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            subprocess.run(["git", "init", "-q"], cwd=p, check=True)
            for n in range(101):
                (p / f"file{n:03d}.py").write_text("x=1\n", encoding="utf-8")
            report = evidence.collect(p)
            self.assertFalse(report["available"])
            self.assertIn("100", report["reason"])


if __name__ == "__main__":
    unittest.main()
