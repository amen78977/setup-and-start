"""Platform and JSON-event adapters; never invoke paid models."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "setup-and-start" / "scripts"
spec = importlib.util.spec_from_file_location("compat_router", SCRIPTS / "router.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class CliCompatibilityTests(unittest.TestCase):
    def test_opencode_final_review_event(self):
        event = {"type": "text", "part": {"text": '{"approved":true,"issues":[]}'}}
        self.assertTrue(router.parse_review(json.dumps(event))["approved"])

    def test_opencode_small_discovery_event(self):
        details = {"files": ["src/app.ts"], "risks": [], "acceptance": ["Build passes"]}
        event = {"type": "text", "part": {"text": json.dumps(details)}}
        self.assertEqual(router.delegate.parse(json.dumps(event)), details)

    @unittest.skipUnless(os.name == "nt", "Windows-specific executable shim")
    def test_npm_shim_launches_via_node_executable(self):
        if not shutil.which("npm") or not shutil.which("node"):
            self.skipTest("Node/npm unavailable")
        resolved = router.safe_windows_launcher(["npm", "--version"])
        self.assertNotIn(Path(resolved[0]).suffix.lower(), (".cmd", ".bat"))
        with tempfile.TemporaryDirectory() as d:
            result = router.execute(["npm", "--version"], Path(d), 30)
        self.assertEqual(result.returncode, 0, result.stderr[:300])

    @unittest.skipUnless(os.name == "nt", "Windows-specific executable shim")
    def test_opencode_prompt_never_goes_to_cmd_interpreter(self):
        if not shutil.which("opencode"):
            self.skipTest("OpenCode not available")
        prompt = "literal & | > < % ^ ! task " * 450
        launch = router.safe_windows_launcher(["opencode", "run", prompt])
        self.assertNotIn(Path(launch[0]).suffix.lower(), (".cmd", ".bat"))
        self.assertEqual(launch[-1], prompt)
        with tempfile.TemporaryDirectory() as d:
            result = router.execute(["opencode", "--version"], Path(d), 30)
        self.assertEqual(result.returncode, 0, result.stderr[:300])


if __name__ == "__main__":
    unittest.main()
