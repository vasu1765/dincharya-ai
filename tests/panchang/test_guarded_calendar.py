"""Owner-approved references, isolated development safety and real transitions."""
from datetime import date, timedelta
import os
import unittest

from prototypes.panchang.astronomy import Astronomy, Unsupported
from prototypes.panchang.guarded import guarded_occurrence
from prototypes.panchang.recurrence import LunarRule


@unittest.skipUnless(os.environ.get("DINCHARYA_PUBLIC_DE440S"), "requires pinned public kernel")
class GuardedCalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.astronomy = Astronomy(os.environ["DINCHARYA_PUBLIC_DE440S"])
        cls.addClassCleanup(cls.astronomy.close)

    def select(self, day, rule, **kwargs):
        start = date.fromisoformat(day)
        return guarded_occurrence(self.astronomy, rule, start, start + timedelta(days=5), **kwargs)

    def test_june_30_sunrise_model_disagreement_withholds_both_tithis(self):
        for rule in (LunarRule("shukla", 15, "ordinary", repeated="first"),
                     LunarRule("krishna", 1, "ordinary", repeated="last")):
            with self.subTest(rule=rule), self.assertRaisesRegex(Unsupported, "sunrise_models_disagree"):
                self.select("2026-06-29", rule)

    def test_may_1_reference_uncertainty_enters_300_second_guard(self):
        rule = LunarRule("krishna", 7, "ordinary", "amanta", "chaitra")
        clean = self.select("2024-05-01", rule, endpoints=())
        self.assertEqual(clean["selected_date"], "2024-05-01")
        self.assertGreater(clean["minimum_margin_seconds"], 300)
        with self.assertRaisesRegex(Unsupported, "boundary_uncertainty"):
            self.select("2024-05-01", rule)

    def test_conflicting_comparable_delhi_tithi_is_withheld(self):
        rule = LunarRule("shukla", 12, "ordinary", month="chaitra", repeated="first")
        with self.assertRaisesRegex(Unsupported, "delhi_reference_disagreement"):
            self.select("2023-04-01", rule, references=(("2023-04-02", 11),))

    def test_repeat_policy_and_skip(self):
        for repeated, expected in (("first", "2023-04-02"), ("last", "2023-04-03")):
            rule = LunarRule("shukla", 12, "ordinary", month="chaitra", repeated=repeated)
            self.assertEqual(self.select("2023-04-01", rule)["selected_date"], expected)
        cases = [
            ("2023-04-01", LunarRule("shukla", 12, "ordinary", month="chaitra"), "repeated_requires_policy"),
            ("2023-04-09", LunarRule("krishna", 6, "ordinary", month="vaishakha"), "skipped_at_sunrise"),
        ]
        for day, rule, reason in cases:
            with self.subTest(day=day), self.assertRaisesRegex(Unsupported, reason):
                self.select(day, rule)

    def test_month_convention_and_adhika_identity_are_preserved(self):
        for convention in ("amanta", "purnimanta"):
            adhika = self.select("2023-07-17", LunarRule("shukla", 1, "adhika", convention, "shravana"))
            regular = self.select("2023-08-16", LunarRule("shukla", 1, "ordinary", convention, "shravana"))
            self.assertEqual(adhika["identity"]["convention"], convention)
            self.assertEqual(adhika["identity"]["intercalation"], "adhika")
            self.assertEqual(regular["identity"]["intercalation"], "ordinary")
            self.assertNotEqual(adhika["identity"]["lunation_cycle"], regular["identity"]["lunation_cycle"])

    def test_kshaya_month_is_withheld(self):
        # Lunar month with two solar ingresses from the preserved research suite.
        start = date(1983, 1, 15)
        with self.assertRaisesRegex(Unsupported, "unsupported_month_calculation"):
            guarded_occurrence(self.astronomy, LunarRule("shukla", 9, "both"),
                               start, start + timedelta(days=28))
