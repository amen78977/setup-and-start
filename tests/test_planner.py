import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / "skills" / "setup-and-start" / "scripts"
spec = importlib.util.spec_from_file_location("routing_module", ROOT / "router.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class PlannerTests(unittest.TestCase):
    def test_ui_is_phase_bounded(self):
        task = "تصميم واجهة responsive RTL لكن بدون backend"
        ids = [p["id"] for p in router.route(task, "build")]
        self.assertIn("frontend", ids)
        self.assertNotIn("backend", ids)

    def test_no_false_substring_match(self):
        self.assertFalse(router.planner.matched_terms("capital investment", ["api"]))
        self.assertFalse(router.planner.matched_terms("beautiful building", ["ui"]))

    def test_plan_has_all_phases_and_bounds(self):
        doc = router.planner.make_plan("build a web UI API test", limit=2)
        self.assertEqual(len(doc["phases"]), 5)
        self.assertTrue(all(len(x["packs"]) <= 2 for x in doc["phases"]))
        self.assertIn("verification", doc["phases"][3]["packs"])
        self.assertIn("verification", doc["phases"][4]["packs"])

    def test_project_discovery_never_reads_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "package.json").write_text('{"scripts":{"test":"echo x"}}', encoding="utf-8")
            (folder / ".env").write_text("SUPER_SECRET_SENTINEL", encoding="utf-8")
            doc = router.planner.project_signals(folder)
            self.assertIn("frontend", doc["detected"])
            self.assertNotIn("SUPER_SECRET_SENTINEL", str(doc))

    def test_reference_size_is_hard_bounded(self):
        loaded = router.planner.read_guidance(router.route("frontend UI", "build"), max_chars=256)
        self.assertLessEqual(len(loaded), 256)

    def test_auto_checks_are_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "tests").mkdir()
            (p / "tests" / "test_foo.py").write_text("pass", encoding="utf-8")
            self.assertIn("-m", router.auto_checks(p)[0])


if __name__ == "__main__":
    unittest.main()
