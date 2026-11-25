"""Run inside the pinned application image with recorded I/O only."""
import unittest
from unittest.mock import Mock

from dincharya.daily_sdk import RecordedSDK


class WireTests(unittest.TestCase):
    def setUp(self):
        self.reserve = Mock(return_value=True)
        self.sdk = RecordedSDK(903, 904, lambda: 81, self.reserve, lambda: False)
        self.addCleanup(self.sdk.close)

    def test_poll_send_edit_answer(self):
        update = {"update_id": 7, "message": {"message_id": 4, "date": 1000, "text": "/rules",
                  "from": {"id": 903, "is_bot": False, "first_name": "Owner"},
                  "chat": {"id": 903, "type": "private"}}}
        self.assertEqual(self.sdk.poll_one(update)["message"]["date"], 1000)
        preview = self.sdk("sendMessage", {"chat_id": 903, "text": "Review",
            "reply_markup": {"inline_keyboard": [[{"text":"Confirm","callback_data":"confirm/test"}]]}})
        self.assertEqual(preview["result"]["reply_markup"]["inline_keyboard"][0][0]["callback_data"], "confirm/test")
        edited = self.sdk("editMessageText", {"chat_id":903,"message_id":81,"text":"Confirmed",
                          "reply_markup":{"inline_keyboard":[]}})
        self.assertEqual(edited["result"]["message_id"],81)
        self.assertFalse((edited["result"].get("reply_markup") or {}).get("inline_keyboard"))
        self.assertIs(self.sdk("answerCallbackQuery", {"callback_query_id":"fixture","text":"Already confirmed"})["result"], True)
        self.assertEqual(self.reserve.call_count,3)

    def test_signed_daily_routes_use_sdk_receipts(self):
        from datetime import datetime, timezone
        from uuid import uuid4
        from dincharya.personal_recorded import PersonalReview, dispatch_recorded
        db=Mock(autocommit=True)
        row=db.execute.return_value.fetchone
        row.side_effect=[PersonalReview.database_identity,(True,)]
        lookup=Mock(side_effect=lambda q,d:"Delhi details" if d else "Delhi tithi")
        review=PersonalReview(db,"a"*40,903,904,self.sdk,lookup)
        now=datetime.now(timezone.utc)
        def submit(text):
            raw={"update_id":9,"message":{"message_id":9,"date":int(now.timestamp()),"text":text,
                 "from":{"id":903,"is_bot":False,"first_name":"Owner"},"chat":{"id":903,"type":"private"}}}
            return dispatch_recorded(review,self.sdk.poll_one(raw),now)
        for query,expected in [("tithi on 2023-12-06","Delhi tithi"),("/details tithi on 2023-12-06","Delhi details")]:
            row.side_effect=[(uuid4(),),(True,)]
            self.assertEqual(submit(query),expected)
        target=uuid4()
        for command in (f"/cancel {target}",f"/modify {target} Schedule Reading every day at 20:30"):
            row.side_effect=[(uuid4(),uuid4(),"Original"),(True,)]
            self.assertEqual(submit(command),"preview")
        self.assertEqual(self.reserve.call_count,4)
        self.assertFalse(any("ui_decide" in call.args[0] for call in db.execute.call_args_list))

    def test_unreviewed_observance_with_civil_date_is_withheld(self):
        from dincharya.personal_recorded import PersonalReview
        review = Mock()
        review.reply.return_value = "withheld"
        for name in ("Ram Navami", "Janmashtami", "Smarta Ekadashi", "वैष्णव एकादशी"):
            result = PersonalReview.message(review, {"update_id":1},
                       {"text":"Schedule "+name+" every year on 03-26 at 07:00"}, None)
            self.assertEqual(result,"withheld")
        review.change_draft.assert_not_called()

    def test_exhaustion_precedes_transport(self):
        self.reserve.return_value = False
        with self.assertRaises(RuntimeError):
            self.sdk("sendMessage", {"chat_id":903,"text":"Blocked"})
        self.assertFalse(self.sdk.backend.calls)


if __name__ == "__main__":
    unittest.main()
