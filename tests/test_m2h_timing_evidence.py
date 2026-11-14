"""Evidence-only regression for Panchang timing sensitivity and date guard.

Run: python3 -m unittest discover -s tests -p 'test_m2h_timing_evidence.py'
No astronomy dependency, network, database, Telegram or production access.
"""
import json
import unittest
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "prototypes" / "panchang"
FILES = {
    "feasibility": "feasibility-results.json",
    "validation": "validation-results.json",
    "recurrence": "recurrence-results.json",
}
THRESHOLDS = (60, 90, 120)
SUNRISE_GUARD_SECONDS = 300


def load_evidence():
    return {name: json.loads((RESULTS / filename).read_text(encoding="utf-8"))
            for name, filename in FILES.items()}


def selected_rows(evidence):
    """Use one baseline coordinate convention; exclude nine alternatives."""
    rows = []
    for item in evidence["feasibility"]["comparisons"]:
        rows.append((item["source"], item["published_at"], item["delta_seconds"]))
    for item in evidence["validation"]["additional_transitions"]:
        rows.append((item["reference"]["source"], item["reference"]["at"],
                     item["delta_seconds"]))
    for item in evidence["recurrence"]["new_timing_diagnostics"]:
        rows.append((item["reference"]["source"], item["reference"]["at"],
                     item["delta_seconds"]))
    return rows


def threshold_counts(rows):
    return {t: (sum(abs(delta) <= t for _, _, delta in rows),
                sum(abs(delta) > t for _, _, delta in rows))
            for t in THRESHOLDS}


def conservative_date_evidence(day):
    """Research-only classification; never returns a schedulable date."""
    hypotheses = day["hypotheses"]
    matches = bool(hypotheses) and all(
        h["matches"] and h["ordinal"] == day["reference"]["ordinal"]
        for h in hypotheses
    )
    far_from_boundary = bool(hypotheses) and all(
        h["boundary_distance_seconds"] > SUNRISE_GUARD_SECONDS
        for h in hypotheses
    )
    return {"reference_match": matches, "outside_guard": far_from_boundary,
            "eligible_for_live_scheduling": False}


class TimingEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = load_evidence()
        cls.rows = selected_rows(cls.evidence)

    def test_baseline_counts_and_threshold_sensitivity(self):
        self.assertEqual(len(self.rows), 13)
        self.assertEqual(threshold_counts(self.rows),
                         {60: (9, 4), 90: (12, 1), 120: (12, 1)})

    def test_unique_source_reference_rows(self):
        keys = [(source, instant) for source, instant, _ in self.rows]
        self.assertEqual(len(keys), len(set(keys)))
        for _, instant, delta in self.rows:
            self.assertIsNotNone(datetime.fromisoformat(instant).utcoffset())
            self.assertIsInstance(delta, (int, float))

    def test_publisher_disagreement_remains_visible(self):
        source_deltas = {source: delta for source, _, delta in self.rows}
        self.assertAlmostEqual(source_deltas["drik2026"], 82.479851)
        self.assertAlmostEqual(source_deltas["panchangam2026"], 22.494496)
        self.assertLess(abs(source_deltas["panchangam2026"]), 60)
        self.assertGreater(abs(source_deltas["drik2026"]), 60)
        self.assertGreater(abs(source_deltas["himalayan2025"]), 120)

    def test_alternative_conventions_not_counted_as_independent_events(self):
        self.assertEqual(len(self.evidence["validation"]["controlled_conventions"]), 9)
        self.assertEqual(len(self.evidence["feasibility"]["comparisons"]), 5)
        self.assertEqual(len(self.evidence["validation"]["additional_transitions"]), 6)
        self.assertEqual(len(self.evidence["recurrence"]["new_timing_diagnostics"]), 2)

    def test_research_calendar_days_do_not_authorize_scheduling(self):
        days = self.evidence["recurrence"]["calendar_days"]
        self.assertEqual(len(days), 11)
        for day in days:
            result = conservative_date_evidence(day)
            self.assertFalse(result["eligible_for_live_scheduling"])
            if result["reference_match"] and result["outside_guard"]:
                self.assertTrue(all(h["matches"] for h in day["hypotheses"]))

    def test_unsupported_recurrence_remains_unschedulable(self):
        self.assertFalse(self.evidence["recurrence"]["usable_for_scheduling"])
        self.assertFalse(self.evidence["validation"]["usable_for_scheduling"])
        self.assertFalse(self.evidence["feasibility"]["usable_for_scheduling"])

    def test_guard_is_independent_of_timing_threshold(self):
        self.assertEqual(SUNRISE_GUARD_SECONDS, 300)
        self.assertGreater(SUNRISE_GUARD_SECONDS, max(THRESHOLDS))
        synthetic = {"reference": {"ordinal": 8}, "hypotheses": [
            {"ordinal": 8, "matches": True, "boundary_distance_seconds": 250}
        ]}
        self.assertFalse(conservative_date_evidence(synthetic)["outside_guard"])
        self.assertFalse(conservative_date_evidence(synthetic)["eligible_for_live_scheduling"])


if __name__ == "__main__":
    unittest.main()
