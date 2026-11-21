import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "raspberry_pi"))

from severity_policy import classify_severity, load_severity_policy  # noqa: E402


class SeverityPolicyTests(unittest.TestCase):
    def test_default_policy_is_explicitly_provisional(self):
        policy = load_severity_policy(ROOT / "models" / "severity_policy.json")
        self.assertEqual(policy["status"], "PROVISIONAL_REQUIRES_BOARD_LEVEL_VALIDATION")
        self.assertEqual(policy["rules"]["missing_hole"]["severity"], "MEDIUM")
        self.assertEqual(policy["rules"]["open_circuit"]["severity"], "HIGH")
        self.assertEqual(policy["rules"]["short_circuit"]["severity"], "HIGH")

    def test_policy_returns_a_rationale_for_each_target_class(self):
        policy = load_severity_policy()
        for name in ("missing_hole", "open_circuit", "short_circuit"):
            severity, basis = classify_severity(name, policy)
            self.assertIn(severity, {"LOW", "MEDIUM", "HIGH", "UNASSESSED"})
            self.assertTrue(basis.strip())

    def test_unknown_class_uses_unassessed_fallback(self):
        severity, basis = classify_severity("unexpected_class", load_severity_policy())
        self.assertEqual(severity, "UNASSESSED")
        self.assertIn("No approved rule", basis)


if __name__ == "__main__":
    unittest.main()
