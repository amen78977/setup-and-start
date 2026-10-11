import importlib.util
from pathlib import Path
import sys
import tempfile
import time
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "setup-and-start" / "scripts"
spec = importlib.util.spec_from_file_location("timeout_router", SCRIPTS / "router.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class TimeoutTests(unittest.TestCase):
    def test_timeout_returns_124(self):
        with tempfile.TemporaryDirectory() as directory:
            started = time.monotonic()
            result = router.execute([sys.executable, "-c", "import time; time.sleep(15)"],
                                    Path(directory), 1)
            elapsed = time.monotonic() - started
            self.assertEqual(result.returncode, 124)
            self.assertIn("Timed out", result.stderr)
            self.assertLess(elapsed, 12)


if __name__ == "__main__":
    unittest.main()
