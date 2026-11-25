"""Recorded PTB updates against fresh scoped PG17 logins. No Telegram transport."""
import os
import secrets
import sys
import time
from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4
from zoneinfo import ZoneInfo

import psycopg
from telegram import Update, User

from dincharya.attended_gateway import Gateway, Session, dispatch_sdk_update


owner, bot = 93001, 93002
bot_user = User(bot, "Fixture", True)
actor = {"id": owner, "first_name":"Owner", "is_bot":False}
chat = {"id":owner,"type":"private"}
key = secrets.token_hex(32)
sent = []


def record(chat_id, **payload):
    assert chat_id == owner
    msg = {"chat":chat,"from":bot_user.to_dict(),"message_id":len(sent)+1,
           "date":int(time.time()), **payload}
    sent.append(msg)
    return {"ok":True, "result":msg}


def connect(role):
    return psycopg.connect(host="db", dbname="dincharya_attended_test", user="attended_"+role,
                           password=os.environ[role.upper()+"_PASSWORD"], autocommit=True)


def session(conn, role):
    return Session(conn, "attended_"+role, owner, bot, bot_user.to_dict, record)


def reject(call, expected):
    try:
        call()
    except expected:
        return
    raise AssertionError("Expected rejection")


def journey(mode):
    with connect("poller") as poll, connect("worker") as work:
        gate = Gateway(session(poll, "poller"), key)
        worker = session(work, "worker")
        for role in ("worker","poller"):
            with connect(role) as other:
                reject(lambda: session(other, role), RuntimeError)

        def submit(number, **data):
            update = Update.de_json({"update_id":number, **data}, SimpleNamespace(id=bot))
            dispatch_sdk_update(update, bot_user, owner, key, gate.handle)

        def draft(number, when, remind):
            msg = {"chat":chat, "from":actor, "message_id":number, "date":int(time.time()),
                   "text":"Schedule Practice on "+when.strftime("%Y-%m-%d at %H:%M")+
                          ("; at start" if remind else "")}
            submit(number, message=msg)
            reject(lambda: submit(number, message=msg), psycopg.Error)
            return sent[-1]

        def decide(number, msg, confirm):
            cb = {"id":str(number),"from":actor,"chat_instance":"fixture","message":msg,
                  "data":msg["reply_markup"]["inline_keyboard"][0][0 if confirm else 1]["callback_data"]}
            submit(number, callback_query=cb)
            reject(lambda: submit(number,callback_query=cb), psycopg.Error)

        due = (datetime.now(ZoneInfo("Asia/Kolkata"))+timedelta(minutes=2)).replace(second=0,microsecond=0)
        if mode == "disabled":
            reject(lambda: draft(1,due,False), psycopg.Error)
            assert not sent
            return
        if mode == "expired":
            msg = record(owner, text="Fixture")["result"]
            msg["reply_markup"] = {"inline_keyboard":[[{"callback_data":"confirm/"+os.environ["EXPIRED_ID"],
                                                        "text":"Confirm"}]]}
            reject(lambda: decide(2,msg,True), psycopg.Error)
            assert len(sent)==1
            return
        if mode == "budget":
            for i in range(3):
                decide(2*i+2, draft(2*i+1,due,False), False)
            assert len(sent)==6
            poll.close()
            with connect("poller") as restarted:
                gate = Gateway(session(restarted,"poller"),key)
                reject(lambda: draft(99,due,False), psycopg.Error)
            assert len(sent)==6
            return
        if mode == "loss":
            gate.s.transport = lambda **kwargs: (_ for _ in ()).throw(TimeoutError())
            reject(lambda: draft(1,due,True), TimeoutError)
            poll.close()
            with connect("poller") as restarted:
                gate = Gateway(session(restarted,"poller"),key)
                reject(lambda: draft(2,due,True), psycopg.Error)
            assert not sent
            return
        if mode == "crash":
            # Simulate process loss after committed reservation and before settlement.
            poll.execute("SELECT * FROM attended.preview(%s,%s,1,'Fixture',%s,false)",(owner,bot,due))
            poll.close()
            with connect("poller") as restarted:
                gate = Gateway(session(restarted,"poller"),key)
                reject(lambda: draft(2,due,True), psycopg.Error)
            assert not sent
            return
        silent = draft(1,due+timedelta(minutes=1),False)
        import copy
        for change in ("origin","token","sender"):
            bad = copy.deepcopy(silent)
            if change == "origin":
                bad["message_id"] += 100
            elif change == "token":
                bad["reply_markup"]["inline_keyboard"][0][0]["callback_data"]="confirm/"+str(uuid4())
            else:
                bad["from"] = actor
            reject(lambda: decide(2,bad,True), (ValueError,psycopg.Error))
        decide(2,silent,True)
        reminder = draft(3,due,True)
        poll.close()
        with connect("poller") as restarted:
            gate = Gateway(session(restarted,"poller"),key)
            decide(4,reminder,True)
        work.close()
        with connect("worker") as restarted:
            worker = session(restarted,"worker")
            time.sleep(max(0,due.timestamp()-time.time())+0.3)
            worker.tick()
            worker.tick()
        assert len(sent)==5 and sent[-1]["text"]=="Practice"


if __name__ == "__main__":
    journey(sys.argv[1])
