from pathlib import Path
import subprocess
import sys
import unittest


class BenchmarksTests(unittest.TestCase):
    def test_offline_routing_cases(self):
        root = Path(__file__).resolve().parents[1]
        process = subprocess.run(
            [sys.executable, str(root / "benchmarks" / "evaluate.py")],
            capture_output=True, encoding="utf-8", errors="replace", text=True, timeout=30,
        )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)


if __name__ == "__main__":
    unittest.main()
