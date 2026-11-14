"""Scope the current timing diagnostic without rewriting accepted evidence."""
import unittest

from prototypes.panchang.reference_policy import publisher_comparison, report


class PublisherPolicyTests(unittest.TestCase):
    def test_pubs_are_separate_and_historical_failure_remains_visible(self):
        result = report()
        self.assertEqual(result["publisher_tolerance_seconds"], 90)
        self.assertEqual(result["counts"], {
            "primary": {"total": 3, "within": 3},
            "secondary": {"total": 3, "within": 3},
            "historical": {"total": 2, "within": 1},
            "context": {"total": 5, "within": 5},
        })
        self.assertEqual(len(result["comparisons"]), 13)
        self.assertTrue(any(row["source"] == "himalayan2025"
                            and row["delta_seconds"] < -150 for row in result["comparisons"]))

    def test_inclusive_symmetric_threshold(self):
        for delta, expected in [(90, True), (-90, True), (90.001, False), (-90.001, False)]:
            with self.subTest(delta=delta):
                result = publisher_comparison("drik2026", delta)
                self.assertEqual(result, {"tier": "primary", "within_display_diagnostic": expected})
