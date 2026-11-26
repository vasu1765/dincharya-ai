"""Owner-provisioned Telegram release. Import and default CLI invocation are inert."""
import argparse
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import re
import signal
import time

from dincharya.attended_gateway import identity, positive, private
from dincharya.attended_operator import signed_route, telegram_transport
from dincharya.daily_review import Review
from dincharya.lunar_service import envelope
from dincharya.personal_recorded import PersonalReview
from dincharya.personal_service import deliver_due


@dataclass(frozen=True)
class Approval:
    owner: int
    bot: int
    bot_username: str
    revision: str
    host: str
    profile: str
    start: int
    end: int
    commands: tuple

    @classmethod
    def read(cls, raw, revision, host, clock=time.time):
        value=json.loads(raw)
        if not isinstance(value,dict) or set(value)!=set(cls.__annotations__):
            raise ValueError("Invalid release fields")
        commands=value["commands"]
        if not isinstance(commands,list) or any(not isinstance(c,str) or not 0<len(c)<=500 for c in commands):
            raise ValueError("Invalid command scope")
        a=cls(**{**value,"commands":tuple(commands)})
        if (not positive(a.owner) or not positive(a.bot) or a.owner==a.bot
            or not re.fullmatch(r"[A-Za-z0-9_]{2,29}[Bb][Oo][Tt]",a.bot_username)
            or not re.fullmatch(r"[0-9a-f]{40}",revision) or a.revision!=revision
            or not host or a.host!=host or type(a.start)!=int or type(a.end)!=int
            or not a.start<=clock()<a.end or a.profile not in ("bounded","daily")
            or (a.profile=="bounded" and (len(set(commands))!=3 or len(commands)!=3 or a.end-a.start>3600))
            or (a.profile=="daily" and commands)):
            raise ValueError("Invalid release scope")
        if a.profile=="bounded":
            # Exact ordered allowlist: a Delhi query, silent one-off and at-start one-off.
            if not re.fullmatch(r"(?:Delhi tithi on|What was the tithi in Delhi on) [0-9]{4}-[0-9]{2}-[0-9]{2}[?]?",commands[0],re.I):
                raise ValueError("Expected one read-only Delhi question")
            times=[]
            for command,suffix in zip(commands[1:],("", "; at start")):
                match=re.fullmatch(r"Schedule ([^;\n]{1,80}) on (\d{4}-\d{2}-\d{2}) at (\d{2}:\d{2})"+suffix,command)
                if not match:
                    raise ValueError("Expected an approved civil one-off")
                dt=datetime.fromisoformat(match[2]+"T"+match[3]).replace(tzinfo=ZoneInfo("Asia/Kolkata"))
                if not a.start<dt.timestamp()<a.end:
                    raise ValueError("Appointment outside release window")
                times.append(dt)
            if times[0]==times[1]:
                raise ValueError("Conflicting appointment times")
        return a


class ExpiredCallback(Exception):
    """Telegram definitively rejected the callback notification."""


class DailyTelegram:
    def __init__(self,client,token,approval,gate,stopped):
        if not re.fullmatch(str(approval.bot)+r":[A-Za-z0-9_-]{20,}",token):
            raise ValueError("Bot token identity mismatch")
        self.client,self.approval=client,approval
        self.base="https://api.telegram.org/bot"+token+"/"
        self.gate,self.stopped=gate,stopped
        self.callback_id=None
        self.verified=False
        self.consumed=set()

    def _call(self,method,body):
        if self.stopped() or method not in ("getMe","getUpdates","sendMessage","editMessageText","answerCallbackQuery"):
            raise RuntimeError("Transport stopped")
        if method!="getMe" and not self.verified:
            raise RuntimeError("Bot identity unverified")
        reply=self.client.post(self.base+method,json=body)
        if method=="answerCallbackQuery" and reply.status_code==400:
            error=reply.json()
            if (error.get("ok") is False and error.get("error_code")==400 and
                error.get("description")=="Bad Request: query is too old and response timeout expired or query ID is invalid"):
                raise ExpiredCallback()
        reply.raise_for_status()
        result=reply.json()
        if result.get("ok") is not True:
            raise ValueError("Missing positive Telegram acknowledgement")
        return result

    def verify(self):
        self.verified=False
        me=self._call("getMe",{})["result"]
        if not identity(me,self.approval.bot,True) or me.get("username")!=self.approval.bot_username:
            raise ValueError("Dedicated bot identity mismatch")
        self.verified=True

    def poll(self,offset):
        return self._call("getUpdates",dict(offset=offset,limit=1,timeout=1,
                          allowed_updates=["message","callback_query"]))["result"]

    def outbound(self,method,body,kind):
        if self.stopped() or not self.verified:
            raise RuntimeError("Transport unavailable")
        if method=="answerCallbackQuery":
            if not self.callback_id or body.get("callback_query_id")!=self.callback_id:
                raise ValueError("Callback origin mismatch")
        elif method not in ("sendMessage","editMessageText") or body.get("chat_id")!=self.approval.owner:
            raise ValueError("Destination mismatch")
        self.gate(kind)
        reply=self._call(method,body)
        if method=="sendMessage" and body.get("reply_markup") and reply["result"].get("reply_markup")!=body["reply_markup"]:
            raise ValueError("Unexpected preview controls")
        return reply

    def __call__(self,method,body):
        return self.outbound(method,body,method)

    def reminder(self,method,body):
        if method!="sendMessage":
            raise ValueError("Invalid reminder operation")
        return self.outbound(method,body,"reminder")


class LiveReview(PersonalReview):
    def __init__(self,conn,key,approval,transport,lookup):
        # Live mode uses its own trusted transport and the existing scoped SQL/receipt checks.
        Review.__init__(self,conn,key,approval.owner,approval.bot,transport)
        self.lookup=lookup

    def message(self,u,m,now):
        text=m.get("text")
        if isinstance(text,str) and re.match(r"^(?:schedule\s|/modify\s|मुझे\s|mujhe\s|remind me\s)",text,re.I):
            withheld=r"ek[aā]da[sś]h?[iī]|deepa[wv]ali|d[iī]p[aā]val[iī]|rama?\s*navam[iī]|janm[aā]s[hṣ]?[tṭ]am[iī]|दीपावली|रामनवमी|एकादशी|जन्माष्टमी|वैष्णव|स्मार्त"
            if re.search(withheld,text,re.I):
                return self.reply(u["update_id"],"This observance needs a reviewed tradition and date rule.")
        return super().message(u,m,now)

    def emit(self,ticket,method,body):
        if ticket is None or method!="answerCallbackQuery":
            return super().emit(ticket,method,body)
        expired=False
        valid=False
        try:
            reply=self.record(method,body)
            valid=reply.get("ok") is True and reply.get("result") is True
        except ExpiredCallback:
            expired=True
        finally:
            if expired:
                sql="SELECT beta.expire_callback(%s,%s,%s)"
                params=(self.owner,self.bot,ticket)
            else:
                sql="SELECT beta.ui_finish(%s,%s,%s,%s,NULL)"
                params=(self.owner,self.bot,ticket,valid)
            if self.conn.execute(sql,params).fetchone()!=(True,):
                raise RuntimeError("Callback settlement requires inspection")


def dispatch(review,tg,update,now,relay):
    a=tg.approval
    if not isinstance(update,dict) or set(update) not in ({"message","update_id"},{"callback_query","update_id"}):
        return
    callback=update.get("callback_query")
    item=callback if callback is not None else update["message"]
    if not isinstance(item,dict) or not identity(item.get("from"),a.owner,False):
        return
    msg=item.get("message") if callback is not None else item
    if not isinstance(msg,dict) or not private(msg.get("chat"),a.owner):
        return
    if callback is not None and not identity(msg.get("from"),a.bot,True):
        return
    if callback is None:
        stamp=msg.get("date")
        if type(stamp)!=int or not 0<=now.timestamp()-stamp<=60 or stamp<a.start:
            return
        if a.profile=="bounded":
            command=msg.get("text")
            if command not in a.commands or command in tg.consumed:
                return
            # The bounded database gate prohibits restarting a consumed session.
            tg.consumed.add(command)
    value,sig=envelope(review.key,dict(operation="daily_review",recipient=a.owner,bot_id=a.bot,update=update),
                       update["update_id"],now.timestamp)
    relay(value,sig)
    tg.callback_id=item.get("id") if callback is not None else None
    try:
        review.handle(value,sig,now)
    finally:
        tg.callback_id=None


def run(root,revision,host):
    import httpx
    import psycopg
    from importlib.metadata import version
    import logging
    if version("httpx")!="0.28.1" or version("httpcore")!="1.0.9" or version("psycopg")!="3.2.13":
        raise RuntimeError("Unexpected release dependencies")
    for name in ("httpx","httpcore"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    from dincharya.attended_runtime import WHEEL,KERNEL_SHA,telegram_tls,verify_wheel
    from dincharya.personal_history import lookup
    raw=(root/"approval.json").read_bytes()
    a=Approval.read(raw,revision,host)
    pin=hashlib.sha256(raw).hexdigest()
    stopping=False
    def stop(*_):
        nonlocal stopping
        stopping=True
    for sig in (signal.SIGINT,signal.SIGTERM):
        signal.signal(sig,stop)
    def stopped():
        return stopping or (root/"STOP").exists() or not a.start<=time.time()<a.end
    if stopped():
        raise RuntimeError("Release stopped")
    with ExitStack() as stack:
        def connect(role):
            return stack.enter_context(psycopg.connect(host="db",dbname="dincharya_personal_candidate",user=role,
                password=(root/(role+".key")).read_text().strip(),autocommit=True,connect_timeout=3,
                options="-c statement_timeout=5000 -c lock_timeout=2000"))
        gateway,worker=connect("personal_gateway"),connect("personal_worker")
        for conn in (gateway,worker):
            if conn.execute("SELECT beta.acquire()").fetchone()!=(True,):
                raise RuntimeError("Release ownership unavailable")
        def gate(op,next_id=None):
            if stopped():
                raise RuntimeError("Release stopped")
            return gateway.execute("SELECT beta.live_gate(%s,%s,%s,%s,%s,%s)",
                        (a.owner,a.bot,pin,a.profile,op,next_id)).fetchone()[0]
        key=(root/"relay.key").read_text().strip()
        tls,_=telegram_tls()
        verify_wheel(root/WHEEL)
        with (root/"de440s.bsp").open("rb") as kernel:
            if hashlib.file_digest(kernel,"sha256").hexdigest()!=KERNEL_SHA:
                raise ValueError("Ephemeris identity mismatch")
        def client(transport):
            return stack.enter_context(httpx.Client(transport=transport,timeout=4,trust_env=False,follow_redirects=False))
        tg=DailyTelegram(client(telegram_transport(tls,"laptop-beta")),(root/"bot.key").read_text().strip(),a,gate,stopped)
        review=LiveReview(gateway,key,a,tg,lambda q,d:lookup(q,d,root/"de440s.bsp",root/WHEEL))
        route=stack.enter_context(signed_route(key,client(httpx.HTTPTransport(retries=0,trust_env=False))))
        if worker.execute("SELECT beta.recording_ready()").fetchone()!=(True,):
            raise RuntimeError("Release requires inspection")
        gate("start")
        tg.verify()
        projection=0
        while not stopped():
            offset=gate("check")
            if offset<0:
                return
            if worker.execute("SELECT beta.recording_ready()").fetchone()!=(True,):
                raise RuntimeError("Release requires inspection")
            if time.monotonic()>=projection:
                worker.execute("SELECT beta.roll_forward()")
                projection=time.monotonic()+3600
            deliver_due(worker,tg.reminder,a.owner,a.bot)
            if gate("check")<0:
                return
            batch=tg.poll(offset)
            if not isinstance(batch,list) or len(batch)>1:
                raise ValueError("Unexpected polling batch")
            for update in batch:
                if not positive(update.get("update_id")) or update["update_id"]<offset:
                    raise ValueError("Invalid update sequence")
                dispatch(review,tg,update,datetime.now(timezone.utc),route)
                gate("ack",update["update_id"]+1)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--authorized-root",type=Path)
    p.add_argument("--revision")
    p.add_argument("--host")
    args=p.parse_args()
    if args.authorized_root:
        try:
            if not args.authorized_root.is_absolute():
                raise ValueError("Absolute approval root required")
            run(args.authorized_root,args.revision,args.host)
        except Exception as exc:
            raise SystemExit("Daily release stopped: "+type(exc).__name__) from None
