"""Evidence-only regression for Panchang timing sensitivity and date guard.

Run: python3 -m unittest discover -s tests -p 'test_m2h_timing_evidence.py'
No astronomy dependency, network, database, Telegram or production access.
"""
import json
import os
import unittest
from datetime import datetime, timedelta
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
HORIZONS = ROOT / "tests/panchang/fixtures/horizons-de441-transitions.json"
MINUTE_WINDOWS = {
    "nearest": (-30, 30),
    "floor": (0, 60),
    "either": (-30, 60),
}


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


def residual_bounds(delta, window):
    """Conservative magnitude bounds allowing any instant in a display interval."""
    lower, upper = window
    return max(lower - delta, delta - upper, 0), max(abs(delta - lower), abs(delta - upper))


def interval_counts(rows, window):
    bounds = [residual_bounds(delta, window) for _, _, delta in rows]
    counts = {}
    for threshold in THRESHOLDS:
        within = sum(maximum <= threshold for _, maximum in bounds)
        outside = sum(minimum > threshold for minimum, _ in bounds)
        counts[threshold] = (within, len(bounds) - within - outside, outside)
    return counts


def horizons_crossings():
    cases = json.loads(HORIZONS.read_text(encoding="utf-8"))["cases"]
    for case in cases:
        start = datetime.fromisoformat(case["start_utc"])
        ordinal = case["entering_ordinal"]
        boundary = (ordinal - 1) * 12
        before, after = (
            (moon - sun - boundary + 180) % 360 - 180
            for sun, moon in case["apparent_ecliptic_longitudes_deg"]
        )
        if not before < 0 < after:
            raise ValueError(f"Horizons samples do not bracket tithi {ordinal} at {start}")
        yield (start, ordinal), start + timedelta(seconds=-60 * before / (after - before))


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

    def test_interval_sensitivity_retains_indeterminate_rows(self):
        expected = {
            "nearest": {60: (8, 4, 1), 90: (9, 3, 1), 120: (12, 0, 1)},
            "floor": {60: (6, 6, 1), 90: (12, 0, 1), 120: (12, 0, 1)},
            "either": {60: (5, 7, 1), 90: (9, 3, 1), 120: (12, 0, 1)},
        }
        for name, window in MINUTE_WINDOWS.items():
            with self.subTest(display_assumption=name):
                self.assertEqual(interval_counts(self.rows, window), expected[name])

    def test_minute_intervals_keep_sign_and_outliers(self):
        self.assertEqual(residual_bounds(0, MINUTE_WINDOWS["floor"]), (0, 60))
        self.assertEqual(residual_bounds(60, MINUTE_WINDOWS["floor"]), (0, 60))
        self.assertEqual(residual_bounds(-60, MINUTE_WINDOWS["floor"]), (60, 120))
        for source, _, delta in self.rows:
            minimum, _ = residual_bounds(delta, MINUTE_WINDOWS["either"])
            if source in {"drik_ekadashi", "drik2026"}:
                self.assertGreater(minimum, 0)
            if source == "himalayan2025" and delta < 0:
                self.assertGreater(minimum, 120)

    def test_horizons_crossings_match_all_thirteen_stored_solutions(self):
        crossings = dict(horizons_crossings())
        matched = set()
        for key, group in (
            ("feasibility", "comparisons"),
            ("validation", "additional_transitions"),
            ("recurrence", "new_timing_diagnostics"),
        ):
            for row in self.evidence[key][group]:
                calculated = datetime.fromisoformat(row["calculated_at"])
                event = (calculated.replace(second=0, microsecond=0),
                         row.get("reference", row)["ordinal"])
                matched.add(event)
                with self.subTest(event=event, reference=row.get("reference", row)["source"]):
                    # Research regression for these pinned samples. No release gate.
                    self.assertLess(abs((calculated - crossings[event]).total_seconds()), 0.1)
        self.assertEqual(len(matched), 8)

    def test_unique_source_reference_rows(self):
        keys = [(source, instant) for source, instant, _ in self.rows]
        self.assertEqual(len(keys), len(set(keys)))
        for _, instant, delta in self.rows:
            self.assertIsNotNone(datetime.fromisoformat(instant).utcoffset())
            self.assertIsInstance(delta, (int, float))

    def test_publisher_disagreement_remains_visible(self):
        deltas = {(source, instant): delta for source, instant, delta in self.rows}
        jan13_drik = ("drik_ekadashi", "2026-01-13T15:17:00+05:30")
        jan13_himalayan = ("himalayan2025", "2026-01-13T15:21:00+05:30")
        jan14_himalayan = ("himalayan2025", "2026-01-14T17:53:00+05:30")
        mar27_drik = ("drik2026", "2026-03-27T10:06:00+05:30")
        mar27_panchangam = ("panchangam2026", "2026-03-27T10:07:00+05:30")
        self.assertAlmostEqual(deltas[jan13_drik], 85.8856)
        self.assertAlmostEqual(deltas[jan13_himalayan], -154.138177)
        self.assertAlmostEqual(deltas[jan14_himalayan], 15.65553)
        self.assertAlmostEqual(deltas[mar27_drik], 82.479851)
        self.assertAlmostEqual(deltas[mar27_panchangam], 22.494496)
        self.assertGreater(abs(deltas[jan13_himalayan]), 120)

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
            self.assertTrue(result["reference_match"], day["reference"])
            self.assertTrue(result["outside_guard"], day["reference"])

    def test_unsupported_recurrence_remains_unschedulable(self):
        self.assertFalse(self.evidence["recurrence"]["usable_for_scheduling"])
        self.assertFalse(self.evidence["validation"]["usable_for_scheduling"])
        self.assertFalse(self.evidence["feasibility"]["usable_for_scheduling"])

    def test_boundary_guard_strict_edge_cases(self):
        for seconds, expected in [(0, False), (299.999, False),
                                  (300, False), (300.001, True), (301, True)]:
            with self.subTest(seconds=seconds):
                day = {"reference": {"ordinal": 8}, "hypotheses": [
                    {"ordinal": 8, "matches": True,
                     "boundary_distance_seconds": seconds}
                ]}
                self.assertEqual(
                    conservative_date_evidence(day)["outside_guard"], expected
                )
                self.assertFalse(
                    conservative_date_evidence(day)["eligible_for_live_scheduling"]
                )

    def test_conflicting_tithi_reference_fails_closed(self):
        day = {"reference": {"ordinal": 8}, "hypotheses": [
            {"ordinal": 9, "matches": False,
             "boundary_distance_seconds": 3600}
        ]}
        result = conservative_date_evidence(day)
        self.assertFalse(result["reference_match"])
        self.assertFalse(result["eligible_for_live_scheduling"])

    def test_guard_is_independent_of_timing_threshold(self):
        self.assertEqual(SUNRISE_GUARD_SECONDS, 300)
        self.assertGreater(SUNRISE_GUARD_SECONDS, max(THRESHOLDS))
        synthetic = {"reference": {"ordinal": 8}, "hypotheses": [
            {"ordinal": 8, "matches": True, "boundary_distance_seconds": 250}
        ]}
        self.assertFalse(conservative_date_evidence(synthetic)["outside_guard"])
        self.assertFalse(conservative_date_evidence(synthetic)["eligible_for_live_scheduling"])


@unittest.skipUnless(os.environ.get("DINCHARYA_PUBLIC_DE440S"), "requires pinned DE440s")
class HorizonsCrossingTests(unittest.TestCase):
    def test_pinned_solver_matches_horizons_for_eight_events_and_two_sunrise_cases(self):
        from prototypes.panchang.astronomy import Astronomy

        crossings = dict(horizons_crossings())
        self.assertEqual(len(crossings), 10)
        with Astronomy(os.environ["DINCHARYA_PUBLIC_DE440S"]) as astronomy:
            for (start, ordinal), crossing in crossings.items():
                with self.subTest(start=start, ordinal=ordinal):
                    rows = astronomy.transitions(start, start + timedelta(minutes=1))
                    self.assertEqual([row["ordinal"] for row in rows], [ordinal])
                    calculated = datetime.fromisoformat(rows[0]["at"])
                    self.assertLessEqual(rows[0]["bracket_seconds"], 0.05)
                    self.assertLess(abs((calculated - crossing).total_seconds()), 0.1)


if __name__ == "__main__":
    unittest.main()
