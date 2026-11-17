"""Cycle 5 parsing and calendar boundary regression checks."""
from datetime import date, datetime
import unittest

from dincharya.lunar_intent import Clarify
from dincharya.recurring import NOTIFICATION_EDIT, notification, parse_recurring, policy_name
from prototypes.panchang.astronomy import DELHI


class RecurringIntentTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2027, 11, 19, 17, 0, tzinfo=DELHI)

    def parse(self, text):
        return parse_recurring(text, self.now.date(), self.now)

    def test_new_routines_default_to_no_slots_in_all_three_languages(self):
        for text in ("Schedule Havan every day at 6:30 AM, but don't remind me.",
                     "मुझे Havan हर दिन को ०६:३० बजे", "mujhe Havan roz at 06:30"):
            with self.subTest(text=text):
                mode, offsets, spec = self.parse(text)
                self.assertEqual((mode, offsets, spec["desired"]["start_time"]), ("automatic", [], "06:30"))
                self.assertEqual(spec["desired"]["recurrence_rule"]["start_date"], "2027-11-20")

    def test_weekday_and_leap_day_are_deterministic(self):
        for text in ("Schedule Study class every Friday at 4:30 PM",
                     "मुझे Study class हर शुक्रवार को १६:३० बजे"):
            rule = self.parse(text)[2]["desired"]["recurrence_rule"]
            self.assertEqual((rule["start_date"], rule["frequency"], rule["weekdays"]),
                             ("2027-11-26", "weekly", [5]))
        rule = self.parse("Schedule Leap day every year on 02-29 at 18:30")[2]["desired"]["recurrence_rule"]
        self.assertEqual((rule["start_date"], rule["months"], rule["month_days"]), ("2028-02-29", [2], [29]))
        with self.assertRaises(Clarify):
            self.parse("Schedule Invalid every year on 02-30 at 18:30")

    def test_policy_and_named_edit(self):
        edit = NOTIFICATION_EDIT.fullmatch("Remind me 15 minutes before my Friday study class.")
        self.assertEqual(edit.groups(), ("15 minutes", "Friday study class"))
        for text, expected, policy in (
                ("none", [], "none"), ("at start", [0], "at_start"),
                ("१ दिन और १ घंटे", [60, 1440], "before_start"),
                ("15 minutes before, at start", [0, 15], "before_and_at_start")):
            offsets = notification(text)
            self.assertEqual(offsets, expected)
            self.assertEqual(policy_name(offsets), policy)
        for invalid in ("15 minutes, 15 minutes", "8 days", "0 minutes", "no reminder, at start"):
            with self.subTest(text=invalid), self.assertRaises(Clarify):
                notification(invalid)
        with self.assertRaises(Clarify):
            self.parse("Schedule Walk every day at 06:30, but don't remind me; at start")

    def test_lunar_fields_are_explicit(self):
        base = 'Remind me "Family puja" every year for lunar Chaitra Shukla Navami Purnimanta ordinary first in 2028 at 7 AM'
        mode, offsets, rule = self.parse(base + "; approve future years automatically; at start")
        self.assertEqual((mode, offsets, rule["time"]), ("automatic", [0], "07:00"))
        self.assertEqual((rule["rule"]["convention"], rule["rule"]["repeated"]), ("purnimanta", "first"))
        self.assertEqual(self.parse(base + "; manual")[0], "manual")
        with self.assertRaises(Clarify):
            self.parse(base.replace("ordinary", "both"))
