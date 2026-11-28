from datetime import datetime, timezone
import json
import unittest
from unittest.mock import Mock, patch

import httpx

from dincharya.daily_live import DailyTelegram, LiveReview
from dincharya.feedback_intent import civil_relative, panchang_question, parse_followup
from dincharya.historical_panchang import historical_text
from dincharya.lunar_intent import Clarify
from dincharya.personal_lunar import candidate

NOW=datetime(2026,11,28,21,15,tzinfo=timezone.utc)
RULE=dict(month="kartika",convention="amanta",paksha="krishna",tithi=10,
          intercalation="ordinary",repeated="review",birth_basis="instant")
IDENTITY=dict(version=2,month="kartika",convention="amanta",paksha="krishna",tithi=10,
              intercalation="ordinary",lunation_cycle=345)


class FeedbackTest(unittest.TestCase):
    def test_relative_dates_use_delhi_midnight(self):
        self.assertEqual(panchang_question("what is today's tithi?",NOW),"2026-11-29")
        self.assertEqual(panchang_question("/panchang tomorrow",NOW),"2026-11-30")
        self.assertEqual(panchang_question("yesterday",NOW),"2026-11-28")
        self.assertEqual(panchang_question("and at 7 AM?",NOW,{"day":"2023-12-06"}),"2023-12-06 at 7 AM")
        self.assertEqual(civil_relative("Schedule Study in 10 minutes; at start",NOW),
                         "Schedule Study on 2026-11-29 at 02:55; at start")
        self.assertEqual(civil_relative("Schedule Study tomorrow at 7 PM",NOW),
                         "Schedule Study on 2026-11-30 at 7:00 PM")

    def test_indian_dates_and_foreign_location(self):
        for s in ("6th December 2023 Delhi","06/12/2023 Delhi","6-12-2023 Delhi","६.१२.२०२३ दिल्ली"):
            self.assertEqual(historical_text(s).day.isoformat(),"2023-12-06")
        for s in ("31/11/2026 Delhi","06/12/2023 Mumbai","12/31/2023 Delhi","2023-12-06 or 6/12/2023"):
            with self.assertRaises(Clarify):
                historical_text(s)

    def test_context_needs_explicit_clear_basis(self):
        control={k:v for k,v in RULE.items() if k!="repeated"}
        got=parse_followup('Remind me "Anniversary" every year at 7 AM; Amanta; ordinary; review',
                           {"basis":{"amanta":control}},NOW)
        self.assertTrue(got["annual"])
        self.assertEqual(got["rule"],RULE)
        with self.assertRaises(Clarify):
            parse_followup("Remind me when this occurs this year",None,NOW)
        with self.assertRaises(Clarify):
            parse_followup("Remind me every year at 7 AM; Amanta; adhika",{"basis":{"amanta":control}},NOW)

    def test_withholds_unvalidated_or_changed_dates(self):
        contradictory=Mock(return_value={"selected_date":"2027-11-22","sunrise_dates":["2027-11-22"]})
        self.assertIsNone(candidate(contradictory,RULE,2027))
        self.assertIsNone(candidate(contradictory,RULE,2028))
        contradiction_repeated=Mock(return_value={"selected_date":"2027-11-23","sunrise_dates":["a","b"]})
        self.assertIsNone(candidate(contradiction_repeated,RULE,2027))

    def test_media_and_rule_pagination_one_reply(self):
        review=object.__new__(LiveReview)
        review.reply=Mock()
        review.daily=True
        review.conn=Mock()
        review.owner,review.bot=101,102
        review.message({"update_id":1},{"voice":{"file_id":"fixture"}},NOW)
        review.reply.assert_called_once_with(1,"I can’t process voice messages. Please send the request as text.")
        review.conn.execute.assert_not_called()
        for field,label in (("photo","images"),("video","videos"),("document","documents")):
            review.message({"update_id":2},{field:{}},NOW)
            self.assertIn(label,review.reply.call_args.args[1])
        review.conn.execute.return_value.fetchall.return_value=[(n,"🌙"*80,"lunar annual") for n in range(100)]
        review.message({"update_id":3},{"text":"/rules 7"},NOW)
        value=review.reply.call_args.args[1]
        self.assertIn("page 7/7",value)
        self.assertLess(len(value.encode("utf-16-le")),8000)

    def test_unavailable_calendar_cannot_draft_and_valid_preview_requires_click(self):
        review=object.__new__(LiveReview)
        review.reply=Mock()
        review.daily=True
        review.owner,review.bot=101,102
        review.conn=Mock()
        review.context=(NOW.timestamp()+900,{"basis":{"amanta":{k:v for k,v in RULE.items() if k!="repeated"}}})
        review.pending_intent=None
        review.emit=Mock()
        review.anniversary=Mock(return_value=None)
        update={"update_id":3}
        msg={"text":'Remind me "Sample" every year at 7 AM; Amanta; ordinary'}
        review.message(update,msg,NOW)
        review.conn.execute.assert_not_called()
        review.anniversary.return_value=dict(day="2027-11-23",rule="kartika-amanta-krishna-10",month_kind="ordinary")
        review.conn.execute.return_value.fetchone.return_value=("synthetic-rule","synthetic-ticket")
        self.assertEqual(review.message(update,msg,NOW),"preview")
        text=review.emit.call_args.args[2]
        self.assertIn("Māsa",text["text"])
        self.assertIn("confirm/",text["reply_markup"]["inline_keyboard"][0][0]["callback_data"])
        self.assertIn("beta.ui_draft_lunar",review.conn.execute.call_args.args[0])
        self.assertNotIn("ui_decide",review.conn.execute.call_args.args[0])


class TransportTest(unittest.TestCase):
    def telegram(self,calls,stop,gate,on_request):
        def record(req):
            name=req.url.path.rsplit("/",1)[-1]
            data=json.loads(req.content)
            calls.append((name,data))
            return on_request(name,data)
        a=Mock(bot=102,bot_username="SyntheticBot",owner=101,profile="daily")
        self.client=self.enterContext(httpx.Client(transport=httpx.MockTransport(record)))
        return DailyTelegram(self.client,"102:"+"a"*24,a,gate,stop)

    def test_same_poll_cursor_recovers_and_write_is_never_retried(self):
        calls=[]
        def request(name,data):
            if name=="getUpdates" and len(calls)==1:
                raise httpx.ReadTimeout("private synthetic exception text")
            if name=="sendMessage":
                raise httpx.ReadTimeout("private synthetic exception text")
            return httpx.Response(200,json={"ok":True,"result":[]})
        gate=Mock()
        tg=self.telegram(calls,lambda:False,gate,request)
        tg.verified=True
        with patch("dincharya.daily_live.time.sleep"), patch("dincharya.daily_live.time.monotonic",side_effect=range(20)):
            self.assertEqual(tg.poll(42),[])
        self.assertEqual([entry[1]["offset"] for entry in calls],[42,42])
        with self.assertRaises(httpx.ReadTimeout):
            tg.reminder("sendMessage",{"chat_id":101,"text":"fixture"})
        gate.assert_called_once_with("reminder")
        self.assertEqual([name for name,_ in calls].count("sendMessage"),1)

    def test_stop_during_read_error_prevents_second_read(self):
        calls=[]
        stopped=False
        def request(name,data):
            nonlocal stopped
            stopped=True
            raise httpx.ReadTimeout("synthetic")
        tg=self.telegram(calls,lambda:stopped,Mock(),request)
        with self.assertRaises(RuntimeError):
            tg.verify()
        self.assertEqual(len(calls),1)
