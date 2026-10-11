import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "setup-and-start" / "scripts" / "browser_audit.py"
spec = importlib.util.spec_from_file_location("browser_audit", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class BrowserAuditTests(unittest.TestCase):
    def test_url_is_local_by_default(self):
        self.assertTrue(mod.url_allowed("http://127.0.0.1:3000"))
        self.assertTrue(mod.url_allowed("http://localhost:5173"))
        self.assertFalse(mod.url_allowed("https://example.com"))
        self.assertFalse(mod.url_allowed("file:///etc/passwd"))
        self.assertFalse(mod.url_allowed("http://user:password@localhost:80"))
        self.assertTrue(mod.url_allowed("https://example.com", remote=True))

    def test_assertions(self):
        self.assertTrue(mod.assess({"overflow_px": 0, "broken_images": 0})["pass"])
        bad = mod.assess({"overflow_px": 100, "broken_images": 2, "unnamed_buttons": 1})
        self.assertFalse(bad["pass"])
        self.assertEqual(len(bad["issues"]), 3)


if __name__ == "__main__":
    unittest.main()
