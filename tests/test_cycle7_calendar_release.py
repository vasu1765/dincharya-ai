"""Publisher comparisons for the Cycle 7 personal-calendar release review."""
from datetime import date, datetime, time
import os
import unittest

from dincharya.historical_panchang import HistoricalInput, HistoricalPanchang
from prototypes.panchang.astronomy import Unsupported
from prototypes.panchang.guarded import GuardedCalendar
from prototypes.panchang.recurrence import LunarRule


@unittest.skipUnless(os.environ.get("DINCHARYA_PUBLIC_DE440S"), "requires pinned public kernel")
class ReleaseCalendar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calendar = GuardedCalendar(os.environ["DINCHARYA_PUBLIC_DE440S"])
        cls.historical = HistoricalPanchang(cls.calendar)

    def test_new_delhi_future_navami_reference(self):
        day = date(2027, 4, 15)
        value = self.historical.read(HistoricalInput(day, time(7)))
        # Drik Delhi publishes 13:20; this comparison uses the 90-second display budget.
        published = datetime.fromisoformat("2027-04-15T13:20:00+05:30")
        self.assertLessEqual(abs((datetime.fromisoformat(value["interval"]["end"]) - published).total_seconds()), 90)
        self.assertEqual((value["sunrise"], value["interval"]["ordinal"]), (9, 9))
        self.assertEqual(self.calendar(LunarRule("shukla", 9, "ordinary", "purnimanta", "chaitra", "first"),
                                       date(2027, 4, 14), date(2027, 4, 17))["selected_date"], str(day))

    def test_repeated_sunrise_is_distinct_from_later_instant(self):
        first, second = [self.historical.read(HistoricalInput(date(2023, 4, day), time(7))) for day in (2, 3)]
        self.assertEqual((first["sunrise"], second["sunrise"]), (12, 12))
        self.assertEqual((first["interval"]["ordinal"], second["interval"]["ordinal"]), (12, 13))
        self.assertEqual([m["month"] for m in second["months"].values()], ["chaitra", "chaitra"])
        with self.assertRaisesRegex(Unsupported, "repeated_requires_policy"):
            self.calendar(LunarRule("shukla", 12, "ordinary", "purnimanta", "chaitra"),
                          date(2023, 4, 1), date(2023, 4, 5))

    def test_exceptional_months_preserve_tithi_without_unsupported_identity(self):
        adhika = self.historical.read(HistoricalInput(date(2023, 7, 20), time(7)))
        self.assertEqual(adhika["sunrise"], 3)
        self.assertEqual([(m["month"], m["intercalation"]) for m in adhika["months"].values()],
                         [("shravana", "adhika")] * 2)
        kshaya = self.historical.read(HistoricalInput(date(1983, 1, 23), time(7)))
        self.assertEqual(kshaya["interval"]["ordinal"], 9)
        self.assertEqual(kshaya["months"], {"amanta": None, "purnimanta": None})
