import json
from datetime import datetime, timezone
from pathlib import Path
import unittest
from unittest.mock import Mock

from dincharya.beta_observer import observe
from dincharya.beta_preview import preview
from dincharya.beta_storage import storage_project


class CycleTests(unittest.TestCase):
    def proposal(self, text, chat=101, sender=101):
        return preview({"message": {"chat": {"type": "private", "id": chat},
                                    "from": {"id": sender, "is_bot": False}, "text": text}},
                       101, datetime(2027, 1, 1, tzinfo=timezone.utc))

    def test_four_civil_proposals(self):
        for phrase, frequency, offsets in [
            ("मुझे Havan हर दिन को ०६:३० बजे", "daily", []),
            ("mujhe Study har Friday at 16:30; 15 minutes", "weekly", [15]),
            ("Schedule Dentist on 2027-02-01 at 09:00; at start", "once", [0]),
            ("Schedule Anniversary every year on 02-29 at 11:00", "yearly", []),
        ]:
            with self.subTest(phrase=phrase):
                result = self.proposal(phrase)
                self.assertTrue(result["requires_confirmation"])
                self.assertEqual(result["activity"]["recurrence_rule"]["frequency"], frequency)
                self.assertEqual(result["offset_minutes"], offsets)

    def test_reject_wrong_identity_and_lunar_recurrence(self):
        for chat, sender in [(102, 101), (101, 102)]:
            with self.assertRaises(ValueError):
                self.proposal("Schedule Walk daily at 07:00", chat, sender)
        with self.assertRaisesRegex(ValueError, "withheld"):
            self.proposal("Schedule lunar birthday every year")

    def test_storage_inert_until_digest(self):
        plan = json.loads((Path(__file__).resolve().parents[1] / "docs/beta-runtime-plan.json").read_bytes())
        with self.assertRaises(ValueError):
            storage_project(plan)
        plan["services"]["postgres"]["image"] = "sha256:" + "1" * 64
        pg = storage_project(plan)["services"]["postgres"]
        self.assertEqual((pg["profiles"], pg["network_mode"], pg["restart"]),
                         (["storage-review"], "none", "no"))
        self.assertEqual(pg["pull_policy"], "never")

    def test_observer_alert_transitions(self):
        rev = "a" * 40
        status = dict(project="dincharya-personal-beta", revision=rev, due=0, relay="ready",
                      sending=0, uncertain=0, dead=0)
        results = [dict(status, revision="wrong"), {}, dict(status, uncertain=1), status]
        output = []
        observe("synthetic", rev, 4, probe=Mock(side_effect=[Mock(stdout=json.dumps(r)) for r in results]),
                emit=lambda row: output.append(json.loads(row)), wait=lambda _: None)
        self.assertEqual([r["state"] for r in output],
                         ["unavailable", "unavailable", "review_delivery", "available"])
        self.assertEqual([r["simulated_owner_alert"] for r in output], [True, False, True, True])
