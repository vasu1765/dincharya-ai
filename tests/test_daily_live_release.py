from datetime import datetime, timezone
import json
import unittest
from unittest.mock import Mock

import httpx

from dincharya.daily_live import Approval, DailyTelegram, dispatch


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.scope=dict(owner=903,bot=904,bot_username="FixtureBot",revision="a"*40,host="fixture",profile="bounded",
                        start=100,end=3600,commands=["What was the tithi in Delhi on 2023-12-06?",
                        "Schedule Quiet on 1970-01-01 at 05:45","Schedule Practice on 1970-01-01 at 06:00; at start"])
        self.a=self.approve()
        self.gate=Mock()
        self.stopped=Mock(return_value=False)
        self.request=[]
        self.result={"id":904,"is_bot":True,"username":"FixtureBot"}
        def wire(request):
            self.request.append(request.url.path.rsplit("/",1)[-1])
            if isinstance(self.result,Exception):
                raise self.result
            return httpx.Response(200,json={"ok":True,"result":self.result})
        self.client=httpx.Client(transport=httpx.MockTransport(wire))
        self.addCleanup(self.client.close)
        self.tg=DailyTelegram(self.client,"904:"+"x"*32,self.a,self.gate,self.stopped)

    def approve(self):
        return Approval.read(json.dumps(self.scope).encode(),"a"*40,"fixture",lambda:150)

    def test_scope_window_and_modes(self):
        for key,value in (("revision","b"*40),("host","other"),("end",149),("commands",[]),("profile","daily")):
            with self.subTest(key=key):
                original=self.scope[key]
                self.scope[key]=value
                with self.assertRaises(ValueError):
                    self.approve()
                self.scope[key]=original

    def test_daily_needs_no_bounded_command_list(self):
        self.scope.update(profile="daily",commands=[])
        self.assertEqual(self.approve().profile,"daily")

    def test_bounded_rejects_recurrence_and_out_of_window(self):
        for command in ("Schedule Practice every day at 06:00; at start","Schedule Practice on 1970-01-02 at 06:00; at start"):
            self.scope["commands"][2]=command
            with self.assertRaises(ValueError):
                self.approve()

    def test_identity_before_poll(self):
        self.result["username"]="OtherBot"
        with self.assertRaises(ValueError):
            self.tg.verify()
        with self.assertRaises(RuntimeError):
            self.tg.poll(0)
        self.assertEqual(self.request,["getMe"])

    def test_poll_edit_and_callback(self):
        self.tg.verify()
        self.result=[]
        self.assertEqual(self.tg.poll(11),[])
        self.result={"message_id":17,"text":"Confirmed"}
        self.tg("editMessageText",dict(chat_id=903,message_id=17,text="Confirmed",reply_markup={"inline_keyboard":[]}))
        self.result=True
        self.tg.callback_id="approved"
        self.assertTrue(self.tg("answerCallbackQuery",dict(callback_query_id="approved",text="Already confirmed"))["result"])
        self.assertEqual(self.request,["getMe","getUpdates","editMessageText","answerCallbackQuery"])

    def test_foreign_destination_and_callback_do_not_spend(self):
        self.tg.verify()
        for method,body in [("sendMessage",{"chat_id":905}),("answerCallbackQuery",{"callback_query_id":"other"})]:
            with self.assertRaises(ValueError):
                self.tg(method,body)
        self.gate.assert_not_called()

    def test_reminder_timeout_spent_once(self):
        self.tg.verify()
        self.result=httpx.ReadTimeout("synthetic")
        with self.assertRaises(httpx.ReadTimeout):
            self.tg.reminder("sendMessage",{"chat_id":903,"text":"Reminder"})
        self.gate.assert_called_once_with("reminder")
        self.assertEqual(self.request.count("sendMessage"),1)

    def test_stop_prevents_network(self):
        self.stopped.return_value=True
        with self.assertRaises(RuntimeError):
            self.tg.verify()
        self.assertEqual(self.request,[])

    def test_unapproved_bounded_text_never_reaches_relay(self):
        update={"update_id":1,"message":{"from":{"id":903,"is_bot":False},"chat":{"id":903,"type":"private"},"text":"other","date":150}}
        relay=Mock()
        dispatch(Mock(),self.tg,update,datetime.fromtimestamp(150,timezone.utc),relay)
        relay.assert_not_called()


class CallbackOutcomeTests(unittest.TestCase):
    def test_explicit_expired_answer_has_distinct_terminal_record(self):
        from dincharya.daily_live import LiveReview, ExpiredCallback
        review=Mock(owner=903,bot=904)
        review.record.side_effect=ExpiredCallback()
        review.conn.execute.return_value.fetchone.return_value=(True,)
        LiveReview.emit(review,17,"answerCallbackQuery",{})
        sql,params=review.conn.execute.call_args.args
        self.assertIn("expire_callback",sql)
        self.assertEqual(params,(903,904,17))

    def test_unknown_answer_is_quarantined(self):
        from dincharya.daily_live import LiveReview
        review=Mock(owner=903,bot=904)
        review.record.side_effect=httpx.ReadTimeout("synthetic")
        review.conn.execute.return_value.fetchone.return_value=(False,)
        with self.assertRaises(RuntimeError):
            LiveReview.emit(review,17,"answerCallbackQuery",{})
        sql,params=review.conn.execute.call_args.args
        self.assertIn("ui_finish",sql)
        self.assertEqual(params,(903,904,17,False))

    def test_stale_command_stays_out_of_relay(self):
        tg=Mock()
        tg.approval=Mock(owner=903,bot=904,start=100,profile="daily")
        update={"update_id":1,"message":{"from":{"id":903,"is_bot":False},"chat":{"id":903,"type":"private"},
                                        "date":110,"text":"/rules"}}
        route=Mock()
        dispatch(Mock(),tg,update,datetime.fromtimestamp(190,timezone.utc),route)
        route.assert_not_called()


class PackagingTests(unittest.TestCase):
    def test_retention_selects_only_surplus_ciphertext(self):
        from pathlib import Path
        import os
        import runpy
        import tempfile
        candidates=runpy.run_path(str(Path(__file__).resolve().parents[1]/"scripts/daily-retention.py"))["candidates"]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for index in range(3):
                p=root/(str(index)*64+".cms")
                p.write_bytes(b"fixture")
                os.utime(p,(100+index,100+index))
            (root/"other.cms").write_text("fixture")
            self.assertEqual(set(candidates(root)),{digit*64+".cms" for digit in ("0","1")})
            self.assertEqual(len(list(root.iterdir())),4)

    def test_renderer_binds_exact_manifest_bytes(self):
        import hashlib
        from pathlib import Path
        import runpy
        provision=runpy.run_path(str(Path(__file__).resolve().parents[1]/"scripts/daily-release-config.py"))["provision"]
        scope={"owner":903,"bot":904,"bot_username":"FixtureBot","revision":"a"*40,"host":"fixture",
               "profile":"daily","start":1,"end":99,"commands":[]}
        raw=json.dumps(scope).encode()
        self.assertIn(hashlib.sha256(raw).hexdigest(),provision(raw,"a"*40,"fixture"))
        with self.assertRaises(ValueError):
            provision(raw,"a"*40,"foreign")
