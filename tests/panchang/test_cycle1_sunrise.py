"""Cycle 1 regressions using the pinned local DE440s kernel."""
from datetime import date, datetime, timedelta
import os
import unittest

from prototypes.panchang.astronomy import Astronomy
from prototypes.panchang.recurrence import DATE_GUARD_SECONDS, LunarRule, RecurrenceResearch


MODELS = ("upper_limb_50", "pac_47_hypothesis")


class Cycle1SunriseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.astronomy = Astronomy(os.environ["DINCHARYA_PUBLIC_DE440S"])
        cls.addClassCleanup(cls.astronomy.close)

    def test_real_transitions_within_guard_withhold_both_tithis(self):
        # Published Delhi labels and the model split are documented in M2H_CYCLE1_ACCURACY.
        cases = (
            ("2023-12-23", 11, (11, 11), (-126, -111)),
            ("2024-08-18", 13, (14, 14), (21, 35)),
            ("2025-12-20", 30, (30, 30), (-255, -240)),
            ("2026-06-30", 15, (15, 16), (-12, 3)),
        )
        for civil_date, ending, ordinals, margins in cases:
            day = date.fromisoformat(civil_date)
            entering = ending % 30 + 1
            for model, ordinal, margin in zip(MODELS, ordinals, margins):
                with self.subTest(day=day, model=model):
                    at_dawn = self.astronomy.at_sunrise(day, model)
                    self.assertEqual(at_dawn["ordinal"], ordinal)
                    key = "end" if ordinal == ending else "start"
                    signed_gap = (
                        datetime.fromisoformat(at_dawn["sunrise"])
                        - datetime.fromisoformat(at_dawn[key])
                    ).total_seconds()
                    self.assertAlmostEqual(signed_gap, margin, delta=1)
                    self.assertLess(abs(signed_gap), DATE_GUARD_SECONDS)
                    preview = RecurrenceResearch(self.astronomy, model)
                    for n in (ending, entering):
                        rule = LunarRule(
                            "shukla" if n <= 15 else "krishna",
                            (n - 1) % 15 + 1, "both", repeated="first",
                        )
                        result = preview.preview(
                            rule, day - timedelta(days=1), day + timedelta(days=2)
                        )
                        self.assertFalse(result["usable_for_scheduling"])
                        self.assertEqual(len(result["occurrences"]), 1)
                        row = result["occurrences"][0]
                        self.assertEqual(row["reason"], "boundary_uncertainty")
                        self.assertIsNone(row["selected_date"])

    def test_saptami_outside_guard_and_ashtami_skipped(self):
        day = date(2024, 5, 1)
        for model in MODELS:
            with self.subTest(model=model):
                preview = RecurrenceResearch(self.astronomy, model)
                for convention, month in (("amanta", "chaitra"), ("purnimanta", "vaishakha")):
                    for tithi, expected, reason in (
                        (7, day.isoformat(), "single_sunrise"),
                        (8, None, "skipped_at_sunrise"),
                    ):
                        rule = LunarRule("krishna", tithi, "ordinary", convention, month)
                        result = preview.preview(rule, day, day + timedelta(days=2))
                        self.assertFalse(result["usable_for_scheduling"])
                        self.assertEqual(len(result["occurrences"]), 1)
                        row = result["occurrences"][0]
                        self.assertEqual(row["selected_date"], expected)
                        self.assertEqual(row["reason"], reason)
