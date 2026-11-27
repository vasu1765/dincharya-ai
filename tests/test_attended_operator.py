from dataclasses import asdict, replace
import hashlib
import json
from unittest import TestCase
from unittest.mock import Mock
from dincharya.attended_operator import Approval, Telegram

class OperatorTests(TestCase):
    def setUp(self):
        from datetime import datetime
        t=int(datetime.fromisoformat("2027-01-01T09:00:00+05:30").timestamp())
        self.a=Approval("a"*40,"acer",*(["sha256:"+"b"*64]*3),902,901,t,t+3600,
            "Schedule Quiet on 2027-01-01 at 09:10","Schedule Reminder on 2027-01-01 at 09:20",
            "What was the tithi on 2023-12-06?","f"*64,"Fixture_bot","93.184.216.34")
        self.c=Mock()
        self.t=Telegram(self.c,"902:"+"t"*32,self.a)

    def load(self,a):
        raw=json.dumps(asdict(a)).encode()
        return Approval.load(raw,hashlib.sha256(raw).hexdigest(),self.a.sha,self.a.host)

    def test_manifest_roundtrip(self):
        self.assertEqual(self.load(self.a),self.a)

    def test_scope_rejections(self):
        for change in [dict(host="elsewhere"),dict(sha="d"*40),dict(owner=101),dict(owner=True),
                       dict(pg="postgres:17"),dict(end=self.a.start+4000),dict(silent=self.a.reminder),
                       dict(reminder="Schedule Reminder on 2027-01-02 at 09:20"),dict(question="/approve")]:
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.load(replace(self.a,**change))

    def test_digest_required(self):
        with self.assertRaises(ValueError):
            Approval.load(b"{}", "a"*64,"a"*40,"acer")

    def test_wrong_username(self):
        self.c.post.return_value.json.return_value={"ok":True,"result":{"id":902,"is_bot":True,"username":"other"}}
        with self.assertRaises(ValueError):
            self.t.me()

    def test_no_retry(self):
        self.c.post.side_effect=TimeoutError()
        with self.assertRaises(TimeoutError):
            self.t.send(chat_id=901,text="Fixture")
        self.c.post.assert_called_once()

    def test_forbidden_operations_and_recipient(self):
        for f in [lambda:self.t.call("answerCallbackQuery",{}),lambda:self.t.send(chat_id=99,text="Fixture")]:
            with self.assertRaises(ValueError):
                f()
        self.c.post.assert_not_called()

    def test_poll_shape(self):
        self.c.post.return_value.json.return_value={"ok":True,"result":[]}
        self.assertEqual(self.t.poll(13),[])
        self.assertEqual(self.c.post.call_args.kwargs["json"],dict(limit=1,timeout=1,offset=13,
                         allowed_updates=["message","callback_query"]))

    def test_unverified_relay_reply(self):
        from dincharya.attended_operator import signed_route
        c=Mock()
        c.post.return_value.json.return_value={"status":"accepted"}
        with signed_route("s"*32,c) as submit,self.assertRaises(ValueError):
            submit({"a":1},"x")
        c.post.assert_called_once()

    def test_forged_and_valid_loopback(self):
        from dincharya.attended_operator import signed_route
        from dincharya.lunar_service import sign
        import httpx
        with httpx.Client(trust_env=False) as local:
            def post(url,json,headers):
                self.assertEqual(url,"http://relay:5678/webhook/m2g-lunar")
                r=local.post("http://127.0.0.1:8080/lunar",json=json,
                             headers={"x-dincharya-signature":"f"*64})
                self.assertEqual(r.status_code,403)
                return local.post("http://127.0.0.1:8080/lunar",json=json,headers=headers)
            value={"nonce":"7"}
            client=Mock()
            client.post.side_effect=post
            with signed_route("s"*32,client) as submit:
                submit(value,sign("s"*32,"command",value))

    def test_default_cli_exits_before_reading_credentials(self):
        from unittest.mock import patch
        from dincharya.attended_operator import main
        with patch("sys.argv",["operator"]),patch("pathlib.Path.read_bytes",side_effect=AssertionError):
            main()

    def test_stopped_or_expired_session_never_contacts_bot(self):
        from dincharya.attended_operator import operate
        for stopped,now in ((True,self.a.start),(False,self.a.end)):
            tg=Mock()
            with self.assertRaises(RuntimeError):
                operate(self.a,"pin",Mock(),Mock(),tg,"k"*32,Mock(),Mock(),lambda:stopped,lambda:now)
            self.assertEqual(tg.mock_calls,[])

    def test_consumed_manifest_prevents_first_network_call(self):
        from dincharya.attended_operator import operate
        from unittest.mock import patch
        db=Mock()
        db.execute.return_value.fetchone.return_value=(False,)
        tg=Mock()
        with patch("dincharya.attended_operator.Session") as session,self.assertRaises(RuntimeError):
            operate(self.a,"pin",db,Mock(),tg,"k"*32,Mock(),Mock(),lambda:False,lambda:self.a.start)
        self.assertEqual(session.call_count,2)
        self.assertEqual(tg.mock_calls,[])
