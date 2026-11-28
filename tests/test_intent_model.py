from datetime import datetime, timezone
import json
from threading import Event
import unittest
from unittest.mock import Mock

import httpx

from dincharya.daily_live import Interpretation, dispatch
from dincharya.intent_model import FIELDS, Provider, Profile, Uninterpretable, as_request, parse


def intent(**values):
    return json.dumps({**dict.fromkeys(FIELDS,""),**values})


class ModelTest(unittest.TestCase):
    def test_strict_grammar_never_takes_execution_metadata(self):
        self.assertEqual(as_request(parse(intent(kind="civil_once",title="Practice",day="tomorrow",clock="07:00")),None),
                         "Schedule Practice tomorrow at 07:00; none")
        with self.assertRaises(Uninterpretable):
            parse(intent(kind="cancel",title="all"))
        with self.assertRaises(Uninterpretable):
            parse(intent(kind="civil_once",title="Practice; SQL",day="today",clock="07:00"))
        with self.assertRaises(Uninterpretable):
            parse(intent(kind="civil_once",title="Practice",day="next Friday",clock="07:00"))
        with self.assertRaises(Uninterpretable):
            parse(intent(kind="clarify")[:-1]+',"kind":"clarify"}')

    def test_lunar_requires_context_and_proposes_only(self):
        i=parse(intent(kind="lunar_annual",title="Anniversary",clock="07:00",repeated="last"))
        self.assertIsNone(as_request(i,None))
        q=as_request(i,{"basis":{"purnimanta":{"title":"fixture"}}})
        self.assertIn("on this tithi every year",q)
        self.assertNotIn("fixture",q)

    def test_local_mock_identity_and_provider_payload(self):
        model,digest="qwen2.5:3b","a"*64
        p=Profile("ollama",model,digest,"http://127.0.0.1:11439",4,0,0,0)
        seen=[]
        def receive(req):
            seen.append(req.url.path)
            if req.method=="GET":
                return httpx.Response(200,json={"models":[{"name":model,"digest":digest}]})
            body=json.loads(req.content)
            self.assertEqual(body["options"]["num_ctx"],2048)
            self.assertNotIn("owner",body["messages"][1]["content"])
            return httpx.Response(200,json={"message":{"content":intent(kind="clarify")}})
        with httpx.Client(transport=httpx.MockTransport(receive)) as c:
            self.assertEqual(Provider(c,p).infer("synthetic",None).kind,"clarify")
            again=Provider(c,Profile("ollama",model,"b"*64,p.endpoint,4,0,0,0))
            with self.assertRaises(Uninterpretable):
                again.infer("synthetic",None)
        self.assertEqual(seen,["/api/tags","/api/chat","/api/tags"])

    def test_cloud_opt_in_and_mocked_response(self):
        config=dict(provider="openai",model="mock",digest="",endpoint="https://api.openai.com",
                    timeout=5,max_calls=3,max_micro_usd=100,per_call_micro_usd=50)
        p=Profile.read(json.dumps(config))
        with self.assertRaises(Uninterpretable):
            Profile.read(json.dumps(config | {"max_calls":0}))
        with self.assertRaises(Uninterpretable):
            Profile.read(json.dumps(config | {"provider":"hybrid"}))
        def receive(req):
            self.assertEqual(req.url.host,"api.openai.com")
            self.assertEqual(req.url.path,"/v1/responses")
            self.assertFalse(json.loads(req.content)["store"])
            return httpx.Response(200,json={"status":"completed","usage":{"input_tokens":30,"output_tokens":15},
                "output":[{"type":"message","content":[{"type":"output_text","text":intent(kind="clarify")}]}]})
        with httpx.Client(transport=httpx.MockTransport(receive)) as c:
            self.assertEqual(Provider(c,p,"synthetic-only").infer("fixture",None).kind,"clarify")

    def test_foreign_updates_never_reach_model_or_relay(self):
        now=datetime(2026,1,1,tzinfo=timezone.utc)
        tg=Mock(approval=Mock(owner=101,bot=102,profile="daily",start=0))
        review=Mock(key="x"*40)
        relay, interpreter=Mock(), Mock()
        update={"update_id":7,"message":{"from":{"id":149,"is_bot":False},
                                      "chat":{"id":149,"type":"private"},"text":"fixture",
                                      "date":int(now.timestamp())}}
        self.assertIsNone(dispatch(review,tg,update,now,relay,interpreter))
        relay.assert_not_called()
        interpreter.offer.assert_not_called()

    def test_one_background_job_and_reserve_before_inference(self):
        latch=Event()
        entered=Event()
        def slow(*_):
            entered.set()
            latch.wait(2)
            return parse(intent(kind="clarify"))
        provider=Mock()
        provider.infer.side_effect=slow
        reserve=Mock(return_value=True)
        q=Interpretation(provider,reserve)
        try:
            job=q.offer("synthetic",None)
            self.assertTrue(entered.wait(1))
            self.assertFalse(job.done())
            self.assertIsNone(q.offer("second",None))
            # Exercise the existing claim/receipt function while the model is blocked.
            from dincharya.personal_service import deliver_due
            when=datetime(2026,1,1,tzinfo=timezone.utc)
            worker=Mock()
            worker.execute.side_effect=[Mock(fetchone=Mock(return_value=(1,2,101,"fixture",when))),
                                        Mock(fetchone=Mock(return_value=(True,)))]
            def reminder(method,body):
                return {"ok":True,"result":{"message_id":3,"from":{"id":102,"is_bot":True},
                        "chat":{"id":101,"type":"private"},"text":body["text"]}}
            deliver_due(worker,reminder,101,102)
            self.assertEqual(worker.execute.call_args.args[1],(1,2,"sent",101,3))
            reserve.assert_called_once()
            latch.set()
            self.assertEqual(job.result(1).kind,"clarify")
            reserve.return_value=False
            self.assertIsNone(q.offer("unfunded",None))
        finally:
            latch.set()
            q.close()
