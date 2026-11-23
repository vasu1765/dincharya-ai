from datetime import datetime, timezone
import unittest
from uuid import uuid4

from dincharya.attended_review import appointment_preview
from dincharya.beta_preview import preview


class AttendedReviewTests(unittest.TestCase):
    def proposal(self, suffix=""):
        update = {"message": {"chat": {"type": "private", "id": 101},
                              "from": {"id": 101, "is_bot": False},
                              "text": "Schedule Practice on 2027-05-16 at 09:30" + suffix}}
        return {**preview(update, 101, datetime(2027, 5, 1, tzinfo=timezone.utc)), "token": str(uuid4())}

    def test_silent_and_at_start(self):
        for suffix, label in [("", "No reminder"), ("; at start", "One reminder at the start")]:
            p = self.proposal(suffix)
            output = appointment_preview(p)
            self.assertIn("2027-05-16 at 09:30 Asia/Kolkata", output["text"])
            self.assertIn(label, output["text"])
            buttons = output["reply_markup"]["inline_keyboard"][0]
            self.assertEqual([b["callback_data"] for b in buttons], [a+"/"+p["token"] for a in ("confirm","cancel")])
            self.assertNotIn("chat_id", output)

    def test_declines_unreviewed_scope(self):
        for changes in [{"requires_confirmation": False}, {"token":"bad"}, {"offset_minutes":[False]},
                        {"notification":"at_start"}, {"status":"active"}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                appointment_preview({**self.proposal(), **changes})
        with self.assertRaises(ValueError):
            appointment_preview(self.proposal("; 15 minutes"))
