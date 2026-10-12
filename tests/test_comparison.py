import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("trial_comparison",
    Path(__file__).resolve().parents[1] / "benchmarks/compare_runs.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ComparisonTests(unittest.TestCase):
    def records(self):
        return [dict(task_id="task", repetition=0, acceptance_id="suite-v1", environment_id="env1",
                     variant=v, acceptance_passed=True, human_interventions=0,
                     usage_complete=True,
                     tokens=t, usd=None, seconds=10) for v, t in (("baseline", 100), ("skill", 80))]

    def test_known_usage_and_unknown_spend_are_distinct(self):
        result = mod.compare(self.records())
        self.assertEqual(result["metrics"]["tokens"]["relative_change"], -.2)
        self.assertIsNone(result["metrics"]["usd"]["relative_change"])
        self.assertFalse(result["metrics"]["usd"]["complete"])

    def test_incomparable_acceptance_is_rejected(self):
        records = self.records()
        records[1]["acceptance_id"] = "different suite"
        with self.assertRaises(ValueError):
            mod.compare(records)

    def test_unpaired_or_duplicate_trials_are_rejected(self):
        for records in (self.records()[:1], self.records() + self.records()[:1], []):
            with self.assertRaises(ValueError):
                mod.compare(records)

    def test_invalid_measurements_rejected(self):
        for value in (-1, float("nan"), float("inf"), True):
            records = self.records()
            records[0]["usd"] = value
            with self.assertRaises(ValueError):
                mod.compare(records)

    def test_quality_regression_is_visible_despite_token_savings(self):
        records = self.records()
        records[1]["acceptance_passed"] = False
        result = mod.compare(records)
        self.assertEqual(result["acceptance_pass_rate"]["skill"], 0)
        self.assertEqual(result["acceptance_pass_rate"]["baseline"], 1)

    def test_partial_usage_is_unknown_and_input_is_preserved(self):
        records = self.records()
        records[1]["usage_complete"] = False
        result = mod.compare(records)
        self.assertEqual(result["metrics"]["tokens"]["measured_pairs"], 0)
        self.assertIsNone(result["metrics"]["tokens"]["relative_change"])
        self.assertEqual(records[1]["tokens"], 80)
