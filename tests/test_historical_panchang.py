"""Historical parsing and independent Delhi publication regressions."""
from datetime import date, datetime, time, timedelta
import json
import os
import unittest

from dincharya.historical_panchang import (HistoricalPanchang, anniversary_text, historical_route, historical_text,
                                          local_instant)
from dincharya.lunar_intent import Clarify
from prototypes.panchang.astronomy import Unsupported
from prototypes.panchang.guarded import GuardedCalendar, REFERENCE_PATH
from prototypes.panchang.recurrence import LunarRule


class HistoricalParserTests(unittest.TestCase):
    def test_bounded_multilingual_forms(self):
        for raw in ("7 December 2023, 4 AM, Delhi — what were the lunar details?",
                    "७ दिसंबर २०२३ को दिल्ली में सुबह ४ बजे क्या तिथि थी?",
                    "7 December 2023 ko Dilli mein subah 4 baje kya tithi thi?"):
            with self.subTest(raw=raw):
                self.assertEqual(historical_route(raw), "historical_panchang")
                event = historical_text(raw)
                self.assertEqual(event.day, date(2023, 12, 7))
                self.assertEqual(event.instant().isoformat(), "2023-12-06T22:30:00+00:00")
        time_only = historical_text("७ दिसंबर २०२३ को दिल्ली में शाम ४ बजे क्या तिथि थी?")
        self.assertEqual(time_only.clock, time(16))
        self.assertIsNone(historical_text("What was the tithi on 6 December 2023?").clock)

    def test_invalid_or_unknown_location_does_not_fall_back(self):
        for raw in ("What was the tithi on 31 February 2023?", "What was the tithi on 2023-12-06 in Melbourne?",
                    "What was the tithi on 2023-12-06 in Delhi and Melbourne?",
                    "What was the tithi on 2023-12-06 4 PM and 6 AM in Delhi?",
                    "What was the tithi on 2023-12-06 at 25:00 in Delhi?"):
            with self.subTest(raw=raw), self.assertRaises(Clarify):
                historical_text(raw)

    def test_historical_timezone_uses_pinned_tzif(self):
        self.assertEqual(local_instant(date(1943, 1, 2), time(10)).time(), time(3, 30))
        self.assertEqual(local_instant(date(2023, 1, 2), time(10)).time(), time(4, 30))
        with self.assertRaises(Clarify):
            local_instant(date(1942, 9, 1), time(0, 30))

    def test_origin_time_never_implies_reminder_time(self):
        example = ("I was born on 22 July 1995 at 14:57 in Delhi. "
                   "Remind me every year on my lunar birthday")
        self.assertEqual(historical_route(example), "draft_historical_anniversary")
        with self.assertRaisesRegex(Clarify, "separate future"):
            anniversary_text(example)
        origin, reminder, mode, convention, repeated, offsets, *_ = anniversary_text(
            example + " at 7 AM; Amanta; manual; last; 15 minutes before")
        self.assertEqual((origin.clock, reminder, mode, convention, repeated, offsets),
                         (time(14, 57), time(7), "manual", "amanta", "last", [15]))


@unittest.skipUnless(os.environ.get("DINCHARYA_PUBLIC_DE440S"), "requires pinned public kernel")
class HistoricalReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.history = HistoricalPanchang(GuardedCalendar(os.environ["DINCHARYA_PUBLIC_DE440S"]))
        cls.refs = json.loads(REFERENCE_PATH.with_name("historical-references.json").read_text())

    def read(self, text):
        event = historical_text(text)
        return self.history.read(event)

    def test_date_only_includes_midnight_and_sunrise(self):
        value = self.read("What was the tithi on 6 December 2023?")
        self.assertEqual((value["day_start"], value["sunrise"]), (23, 24))
        self.assertEqual([row["ordinal"] for row in value["transitions"]], [24])
        self.assertNotIn("instant", value)

    def test_published_boundaries_and_both_month_names(self):
        fixtures = (("6 December 2023 at 10 AM", 24), ("7 December 2023 at 4 AM", 25),
                    ("22 July 1995 at 14:57", 26))
        for (query, ordinal), fixture in zip(fixtures, self.refs["observations"]):
            with self.subTest(query=query):
                value = self.read(query + " in Delhi")
                self.assertEqual(value["interval"]["ordinal"], ordinal)
                self.assertEqual({convention: row["month"] for convention, row in value["months"].items()},
                                 {name: fixture[name] for name in ("amanta", "purnimanta")})
                boundary = "end" if fixture["entering"] != ordinal else "start"
                deviation = datetime.fromisoformat(value["interval"][boundary]) - datetime.fromisoformat(fixture["transition"])
                self.assertLessEqual(abs(deviation.total_seconds()), 90)
                if fixture.get("sunrise_ordinal"):
                    self.assertEqual(value["sunrise"], fixture["sunrise_ordinal"])
        wedding = self.read("7 December 2023 at 4 AM in Delhi")
        self.assertLess(wedding["instant"], min(wedding["dawns"]))
        birth = self.read("22 July 1995 at 14:57 in Delhi")
        self.assertEqual((birth["sunrise"], birth["interval"]["ordinal"]), (25, 26))

    def test_event_precision_is_independent_of_sunrise_guard(self):
        with self.assertRaisesRegex(Unsupported, "transition uncertainty"):
            self.read("7 December 2023 at 03:04:20 in Delhi")
        before = self.read("7 December 2023 at 03:03 in Delhi")
        after = self.read("7 December 2023 at 03:06 in Delhi")
        self.assertEqual((before["interval"]["ordinal"], after["interval"]["ordinal"]), (24, 25))
        self.assertEqual(after["sunrise"], 25)
        self.assertLess((after["instant"] - datetime.fromisoformat(after["interval"]["start"])), timedelta(minutes=5))

    def test_supported_and_unsupported_months_separate_from_tithi(self):
        adhika = self.read("20 July 2023 at 11 AM in Delhi")
        self.assertEqual(adhika["months"]["amanta"]["intercalation"], "adhika")
        kshaya = self.read("23 January 1983 at 11 AM in Delhi")
        self.assertIsNone(kshaya["months"]["amanta"])
        self.assertGreater(kshaya["interval"]["ordinal"], 0)

    def test_future_results_follow_sunrise_and_correlate_with_publisher_days(self):
        for row in self.refs["future_comparisons"]:
            month, convention, paksha, tithi = row["rule"].split("-")
            rule = LunarRule(paksha, int(tithi), "ordinary", convention, month, "first", "instant")
            start, end = date(row["year"], 1, 1), date(row["year"] + 1, 1, 1)
            with self.subTest(rule=rule):
                if row["selected"]:
                    self.assertEqual(self.history.calendar(rule, start, end)["selected_date"], row["selected"])
                else:
                    with self.assertRaisesRegex(Unsupported, row["reason"]):
                        self.history.calendar(rule, start, end)
