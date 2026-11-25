from datetime import date,datetime,time,timezone
import unittest
from unittest.mock import Mock
from uuid import uuid4

from dincharya.daily_review import Review,concise
from dincharya.lunar_service import envelope


class DailyTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2027,5,5,1,tzinfo=timezone.utc)
        self.db=Mock(autocommit=True)
        self.db.execute.return_value.fetchone.return_value=("dincharya_beta_rehearsal","daily_gateway","daily_gateway")
        self.call=Mock()
        self.key="f"*40
        self.ui=Review(self.db,self.key,101,902,self.call)
        self.token=uuid4()
        self.owner={"id":101,"is_bot":False}
        self.bot={"id":902,"is_bot":True}
        self.msg={"chat":{"id":101,"type":"private"},"from":self.bot,"message_id":9}

    def submit(self,**kwargs):
        cmd=dict(operation="daily_review",recipient=101,bot_id=902,update=dict(update_id=7,**kwargs))
        return self.ui.handle(*envelope(self.key,cmd,7,lambda:self.now.timestamp()),self.now)

    def callback(self,action="confirm"):
        return dict(id="fixture",data=action+"/"+str(self.token),message=self.msg,**{"from":self.owner})

    def rows(self,*items):
        self.db.execute.return_value.fetchone.side_effect=items

    def receipt(self,method,body):
        return {"ok":True,"result":True if method=="answerCallbackQuery" else {**self.msg,**body}}

    def test_edit_then_conflicting_callback_never_reopens_buttons(self):
        row=("Practice",date(2027,5,6),time(7))
        self.rows(("active","editMessageText",uuid4(),*row),(True,),
                  ("active","answerCallbackQuery",uuid4(),*row),(True,),
                  ("active","answerCallbackQuery",None,*row))
        self.call.side_effect=self.receipt
        for act in ("confirm","cancel","cancel"):
            self.assertIn("Already confirmed",self.submit(callback_query=self.callback(act)))
        edit,notice=self.call.call_args_list
        self.assertEqual(edit.args[1]["reply_markup"],{"inline_keyboard":[]})
        self.assertIn("06 May 2027",edit.args[1]["text"])
        self.assertEqual(notice.args[0],"answerCallbackQuery")

    def test_unknown_origin_silent(self):
        self.rows(None)
        self.assertEqual(self.submit(callback_query=self.callback()),"denied")
        self.call.assert_not_called()

    def test_expired_terminal_message(self):
        self.rows(("expired","editMessageText",uuid4(),"Study",date(2027,5,6),time(7)),(True,))
        self.call.side_effect=self.receipt
        self.assertIn("expired",self.submit(callback_query=self.callback()))
        self.assertIn("expired",self.call.call_args.args[1]["text"])

    def test_stale_or_foreign_message(self):
        m={**self.msg,"from":self.owner,"date":int(self.now.timestamp())-100,"text":"Schedule Practice"}
        self.assertIn("expired",self.submit(message=m))
        self.assertEqual(self.submit(message={**m,"from":self.bot}),"denied")
        self.call.assert_not_called()

    def test_unsupported_message(self):
        m={**self.msg,"from":self.owner,"date":int(self.now.timestamp()),"text":"/unknown"}
        self.rows((uuid4(),),(True,),(None,))
        self.call.side_effect=self.receipt
        self.assertIn("Please",self.submit(message=m))
        self.assertIn("Please",self.submit(message=m))
        self.call.assert_called_once()

    def test_lost_edit_quarantines(self):
        self.rows(("cancelled","editMessageText",uuid4(),"Study",date(2027,5,6),time(7)),(False,))
        self.call.side_effect=TimeoutError()
        with self.assertRaises(TimeoutError):
            self.submit(callback_query=self.callback("cancel"))
        self.assertIs(self.db.execute.call_args.args[1][3],False)
        self.call.assert_called_once()

    def test_concise_sunrise_and_transition(self):
        from types import SimpleNamespace
        event=SimpleNamespace(day=date(2023,12,6),clock=None)
        value={"sunrise":24,"transitions":[{"ordinal":24,"at":"2023-12-05T19:07:00+00:00"}]}
        answer=concise(event,value,lambda _: "Krishna Navami")
        self.assertEqual(answer,"06 Dec 2023 · New Delhi (IST)\nAt sunrise: Krishna Navami\nKrishna Navami begins at 12:37 AM.")
        self.assertIn("कृष्ण नवमी",concise(event,value,str,devanagari=True))
        value["sunrise"]=None
        self.assertIn("withheld",concise(event,value,str))

    def test_annual_preview_includes_approval_scope_and_offsets(self):
        self.rows((self.token,uuid4()),(True,))
        self.call.side_effect=self.receipt
        m={**self.msg,"from":self.owner,"date":int(self.now.timestamp()),
           "text":"Schedule Practice every year on 05-16 at 09:30; 15 minutes"}
        self.assertEqual(self.submit(message=m),"preview")
        body=self.call.call_args.args[1]
        self.assertIn("Every year on 16 May",body["text"])
        self.assertIn("15 min before",body["text"])
        self.assertIn(str(self.token),body["reply_markup"]["inline_keyboard"][0][0]["callback_data"])

    def test_wrong_edit_receipt_cannot_settle(self):
        self.rows(("active","editMessageText",uuid4(),"Study",date(2027,5,6),time(7)),(False,))
        def wrong(method,body):
            response=self.receipt(method,body)
            response["result"]["message_id"]=999
            return response
        self.call.side_effect=wrong
        with self.assertRaises(RuntimeError):
            self.submit(callback_query=self.callback())
        # The scoped SQL function independently checks the original message ID.
        self.assertEqual(self.db.execute.call_args.args[1][-2:],(False,None))
