from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import Mock
from uuid import uuid4

from dincharya.attended_gateway import Gateway, Session
from dincharya.lunar_service import envelope


class GatewayTests(TestCase):
    def setUp(self):
        self.db = Mock(autocommit=True)
        self.me = {"id": 902, "is_bot": True}
        self.owner = {"id": 901, "is_bot": False}
        self.chat = {"id": 901, "type": "private"}
        self.token = uuid4()
        self.receipt = {"ok": True, "result": {"from": self.me, "chat": self.chat, "message_id": 8}}
        self.send = Mock(return_value=self.receipt)
        self.rows(("dincharya_attended_test", "attended_poller", "attended_poller"), (True,))
        self.session = Session(self.db, "attended_poller", 901, 902, lambda: self.me, self.send)
        self.now = datetime(2027, 5, 15, tzinfo=timezone.utc).timestamp()
        self.key = "s"*40
        self.gate = Gateway(self.session, self.key, lambda: self.now)

    def rows(self, *rows):
        self.db.execute.return_value.fetchone.side_effect = rows

    def signed(self, update):
        return envelope(self.key, {"operation":"attended_update","bot_id":902,"recipient":901,
                                   "update":dict(update_id=42, **update)}, 42, lambda: self.now)

    def message(self, suffix=""):
        return {"message":{"from": self.owner, "chat":self.chat,
                           "text":"Schedule Practice on 2027-05-16 at 09:30" + suffix}}

    def callback(self, action):
        return {"callback_query":{"from":self.owner, "message":{"chat":self.chat, "from":self.me,
                                                                  "message_id":8},
                                  "data":action+"/"+str(self.token)}}

    def test_render_both(self):
        for suffix, expected in [("", "No reminder"), ("; at start","One reminder")]:
            self.rows((self.token, uuid4()), (True,), (True,))
            self.gate.handle(*self.signed(self.message(suffix)))
            self.assertIn(expected,self.send.call_args.kwargs["text"])
            self.assertEqual(self.send.call_args.kwargs["chat_id"],901)

    def test_decisions(self):
        for action in ["confirm","cancel"]:
            self.rows((uuid4(),), (True,), (True,))
            self.gate.handle(*self.signed(self.callback(action)))
            self.assertIn(action,self.send.call_args.kwargs["text"])

    def test_origin_and_signature_denials(self):
        for field, bad in [("chat",{"id":901,"type":"group"}),("from",self.owner),("message_id",True)]:
            update = self.callback("confirm")
            update["callback_query"]["message"][field]=bad
            with self.assertRaises(ValueError):
                self.gate.handle(*self.signed(update))
        value, signature = self.signed(self.message())
        with self.assertRaises(ValueError):
            self.gate.handle(value, "0"*64)
        self.now += 61
        with self.assertRaises(ValueError):
            self.gate.handle(value, signature)
        self.send.assert_not_called()

    def test_wrong_receipt_quarantines(self):
        self.receipt["result"]["chat"]={"id":7,"type":"private"}
        self.rows((self.token, uuid4()), (True,), (False,))
        with self.assertRaises(RuntimeError):
            self.gate.handle(*self.signed(self.message()))
        self.assertIsNone(self.db.execute.call_args.args[1][-1])
        self.send.assert_called_once()

    def test_reservation_rejection_prevents_send(self):
        self.db.execute.side_effect=RuntimeError("closed")
        with self.assertRaises(RuntimeError):
            self.gate.handle(*self.signed(self.callback("confirm")))
        self.send.assert_not_called()

    def test_lost_transport_ack(self):
        self.send.side_effect=TimeoutError()
        self.rows(("Practice",uuid4()), (True,), (False,))
        with self.assertRaises(TimeoutError):
            self.session.tick()
        self.send.assert_called_once()
        self.assertIsNone(self.db.execute.call_args.args[1][-1])

    def test_wrong_signed_bot_or_recipient(self):
        for field in ("bot_id","recipient"):
            value, _ = self.signed(self.message())
            value["command"][field]=777
            signed=envelope(self.key,value["command"],42,lambda: self.now)
            with self.assertRaises(ValueError):
                self.gate.handle(*signed)
        self.send.assert_not_called()

    def test_foreign_sender(self):
        update = self.callback("cancel")
        update["callback_query"]["from"]={"id":99,"is_bot":False}
        with self.assertRaises(ValueError):
            self.gate.handle(*self.signed(update))
        self.send.assert_not_called()

    def test_invalid_uuid_and_action(self):
        for data in ("confirm/not-a-uuid","apply/"+str(self.token),"confirm/"+self.token.hex):
            update=self.callback("confirm")
            update["callback_query"]["data"]=data
            with self.assertRaises(ValueError):
                self.gate.handle(*self.signed(update))
        self.send.assert_not_called()

    def test_session_refuses_other_owner_or_existing_lock(self):
        for role in ("attended_worker","attended_poller"):
            self.rows(("dincharya_attended_test",role,role),(False,))
            with self.assertRaises(RuntimeError):
                Session(self.db,role,901,902,lambda: self.me,self.send)
        with self.assertRaises(ValueError):
            Session(self.db,"attended_worker",101,902,lambda: self.me,self.send)
        with self.assertRaises(ValueError):
            Session(self.db,"attended_worker",901,903,lambda: self.me,self.send)

    def test_expired_or_spent_send_permit(self):
        self.rows((self.token, uuid4()), (False,))
        with self.assertRaises(RuntimeError):
            self.gate.handle(*self.signed(self.message()))
        self.send.assert_not_called()
