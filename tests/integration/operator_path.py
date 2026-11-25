"""Offline Telegram HTTP transcript through the real operator loop and scoped DB."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json
import os
import secrets
import time
from contextlib import ExitStack

import httpx
import psycopg

from beta_relay_journey import install
from dincharya.attended_operator import Approval, Telegram, operate, signed_route, historical, USERNAME

def main():
    raw=Path("/candidate/manifest.json").read_bytes()
    pin=hashlib.sha256(raw).hexdigest()
    a=Approval.load(raw,pin,os.environ["REV"],"operator-fixture")
    key=secrets.token_hex(32)
    bot=dict(id=a.bot,is_bot=True,first_name="Test",username=USERNAME)
    owner=dict(id=a.owner,is_bot=False,first_name="Fixture")
    chat=dict(id=a.owner,type="private")
    replies=[]
    seq=0
    def respond(request):
        nonlocal seq
        method=request.url.path.split("/")[-1]
        payload=json.loads(request.content)
        if method=="getMe":
            result=bot
        elif method=="sendMessage":
            assert payload.pop("chat_id")==a.owner and len(replies)<6
            result=dict(message_id=50+len(replies),date=int(time.time()),chat=chat,**{"from":bot},**payload)
            replies.append(result)
        elif method=="getUpdates":
            seq+=1
            if seq<=5:
                if seq in (3,5):
                    msg=replies[-1]
                    update={"callback_query":{"id":str(seq),"from":owner,"chat_instance":"fixture","message":msg,
                              "data":msg["reply_markup"]["inline_keyboard"][0][0]["callback_data"]}}
                else:
                    text={1:a.question,2:a.silent,4:a.reminder+"; at start"}[seq]
                    update={"message":{"text":text,"message_id":seq,"from":owner,"chat":chat,"date":int(time.time())}}
                result=[dict(update_id=seq,**update)]
            else:
                time.sleep(0.25)
                result=[]
        else:
            raise AssertionError("Unexpected method")
        return httpx.Response(200,json={"ok":True,"result":result})
    with ExitStack() as stack:
        def connect(role):
            return stack.enter_context(psycopg.connect(host="db",dbname="dincharya_attended_test",
                user="attended_"+role,password=os.environ[role.upper()+"_PASSWORD"],autocommit=True))
        poll,work=connect("poller"),connect("worker")
        tg=Telegram(stack.enter_context(httpx.Client(transport=httpx.MockTransport(respond))),
                    str(a.bot)+":"+"s"*32,a)
        client=stack.enter_context(httpx.Client(timeout=5,trust_env=False))
        route=stack.enter_context(signed_route(key,client))
        install(lambda name:print(name,flush=True))
        from beta_relay_journey import wait_for_webhook
        wait_for_webhook(client,lambda _:None)
        operate(a,pin,poll,work,tg,key,route,lambda q: historical(q,Path("/ephemeris/de440s.bsp")),lambda: False)
        assert len(replies)==6 and "2023-12-06" in replies[0]["text"] and "Drik Delhi primary" in replies[0]["text"] and replies[-1]["text"]=="Reminder"
        count=len(replies)
        poll.close()
        work.close()
        try:
            operate(a,pin,connect("poller"),connect("worker"),tg,key,route,None,lambda:False)
        except RuntimeError as exc:
            assert str(exc)=="Disposable approval absent or consumed"
        else:
            raise AssertionError("Operator resumed a consumed session")
        assert len(replies)==count
    print("PASS operator six recorded sends via native relay and fenced restart")
if __name__=="__main__":
    main()
