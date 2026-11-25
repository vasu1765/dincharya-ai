"""One manually started, one-use attended session. All transports are explicit."""
import argparse
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import datetime
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import os
from pathlib import Path
import re
import signal
import socket
import threading
import time

from dincharya.attended_gateway import Gateway, Session, dispatch_sdk_update, identity, positive
from dincharya.lunar_service import sign

RELAY = "http://relay:5678/webhook/m2g-lunar"
from dincharya.attended_connect import PROXY, upstream


@dataclass(frozen=True)
class Approval:
    sha: str
    host: str
    pg: str
    app: str
    n8n: str
    bot: int
    owner: int
    start: int
    end: int
    silent: str
    reminder: str
    question: str
    kernel_sha256: str
    bot_username: str
    telegram_ipv4: str | None = None
    profile: str = "hardened"

    @classmethod
    def load(cls, raw, pin, revision, host):
        if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), pin):
            raise ValueError("Manifest hash mismatch")
        a = cls(**json.loads(raw))
        if a.profile == "hardened":
            upstream(a.telegram_ipv4)
        elif a.profile != "laptop-beta" or a.telegram_ipv4 is not None:
            raise ValueError("Invalid attended profile or destination")

        if (not isinstance(a.bot_username,str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{1,28}[Bb][Oo][Tt]",a.bot_username)
                or a.sha != revision or not re.fullmatch("[0-9a-f]{40}", a.sha)
                or a.host != host or not host or not positive(a.bot) or not positive(a.owner)
                or a.owner in (101,a.bot) or not positive(a.start) or not positive(a.end)
                or not 0 < a.end-a.start <= 3600
                or not all(re.fullmatch("sha256:[0-9a-f]{64}", v) for v in (a.pg,a.app,a.n8n))
                or not re.fullmatch("[0-9a-f]{64}",a.kernel_sha256)
                or not a.question.startswith("What was the tithi on ") or len(a.question)>160
                or a.silent == a.reminder):
            raise ValueError("Invalid approval scope")
        for text in (a.silent,a.reminder):
            if not re.fullmatch(r"Schedule [A-Za-z0-9 ][A-Za-z0-9 ]{0,59} on \d{4}-\d\d-\d\d at \d\d:\d\d", text):
                raise ValueError("Expected one exact civil appointment")
            stamp = datetime.strptime(text.rsplit(" on ",1)[1]+" +0530","%Y-%m-%d at %H:%M %z").timestamp()
            if not a.start < stamp < a.end:
                raise ValueError("Appointment outside session")
        if a.silent.rsplit(" on ",1)[1] == a.reminder.rsplit(" on ",1)[1]:
            raise ValueError("Appointments overlap")
        return a


def telegram_transport(tls, profile="hardened"):
    import httpx
    if profile not in ("hardened","laptop-beta"):
        raise ValueError("Unknown transport profile")
    return httpx.HTTPTransport(proxy=PROXY if profile=="hardened" else None,verify=tls,retries=0,trust_env=False)


class Telegram:
    """Explicit single HTTP request per Bot API operation. No SDK polling supervisor."""
    def __init__(self, client, token, approval):
        if not re.fullmatch(str(approval.bot)+r":[A-Za-z0-9_-]{20,}",token):
            raise ValueError("Bot token identity mismatch")
        self.client, self.base = client, "https://api.telegram.org/bot"+token+"/"
        self.approval = approval

    def call(self, method, body):
        if method not in ("getMe","getUpdates","sendMessage"):
            raise ValueError("Unreviewed Bot API operation")
        r = self.client.post(self.base+method,json=body)
        r.raise_for_status()
        data=r.json()
        if data.get("ok") is not True:
            raise RuntimeError("Telegram rejected operation")
        return data

    def me(self):
        me=self.call("getMe",{})["result"]
        if not identity(me,self.approval.bot,True) or me.get("username") != self.approval.bot_username:
            raise ValueError("Dedicated bot mismatch")
        return me

    def poll(self, offset):
        return self.call("getUpdates",dict(offset=offset,limit=1,timeout=1,
                         allowed_updates=["message","callback_query"]))["result"]

    def send(self, **payload):
        if payload.get("chat_id") != self.approval.owner:
            raise ValueError("Unapproved destination")
        return self.call("sendMessage",payload)


@contextmanager
def signed_route(key, client):
    """Forward through the reviewed n8n workflow. Only consume the pending signed echo."""
    pending = None
    received = False
    lock = threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass
        def do_POST(self):
            nonlocal received
            self.connection.settimeout(2)
            size=int(self.headers.get("Content-Length","0"))
            valid=False
            if self.path == "/lunar" and 0<size<=16384:
                value=json.loads(self.rfile.read(size))
                signature=self.headers.get("x-dincharya-signature","")
                with lock:
                    valid=(pending is not None and value==pending and not received and signature.isascii()
                           and hmac.compare_digest(signature,sign(key,"command",value)))
                    if valid:
                        received=True
            self.send_response(200 if valid else 403)
            self.send_header("Content-Type","application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"accepted"}' if valid else b'{"status":"denied"}')
    class QuietServer(HTTPServer):
        def get_request(self):
            conn, address = super().get_request()
            conn.settimeout(2)
            return conn, address

        def handle_error(self,*args):
            pass
    server=QuietServer(("0.0.0.0",8080),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    def submit(value,sig):
        nonlocal pending,received
        with lock:
            pending,received=value,False
        try:
            r=client.post(RELAY,json=value,headers={"x-dincharya-signature":sig})
            r.raise_for_status()
            with lock:
                if r.json()!={"status":"accepted"} or not received:
                    raise ValueError("Signed relay acknowledgement missing")
        finally:
            with lock:
                pending=None
    try:
        yield submit
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def historical(question, kernel):
    from dincharya.attended_runtime import WHEEL, isolated_lookup
    return isolated_lookup(question, kernel, kernel.with_name(WHEEL))


def operate(a,pin,poll,work,tg,key,route,history,stopped,clock=time.time):
    def guard():
        if stopped() or not a.start<=clock()<a.end:
            raise RuntimeError("Attended session stopped")
    def transport(**payload):
        guard()
        return tg.send(**payload)
    # Both locks and durable one-use approval precede even getMe.
    expected={"id":a.bot,"is_bot":True}
    guard()
    p=Session(poll,"attended_poller",a.owner,a.bot,lambda:expected,transport)
    w=Session(work,"attended_worker",a.owner,a.bot,lambda:expected,transport)
    def query(sql,args):
        return poll.execute(sql,args).fetchone()[0]
    if query("SELECT attended.start_operator(%s,%s,%s,to_timestamp(%s),to_timestamp(%s))",
             (pin,a.owner,a.bot,a.start,a.end)) is not True:
        raise RuntimeError("Disposable approval absent or consumed")
    guard()
    from telegram import Update,User
    from types import SimpleNamespace
    me=User.de_json(tg.me(),None)
    gateway=Gateway(p,key,clock)
    offset=0
    seen_text=set()
    def remaining():
        return query("SELECT attended.remaining(%s,%s)",(a.owner,a.bot))
    while True:
        guard()
        if not remaining():
            return
        w.tick()
        guard()
        if not remaining():
            return
        batch=tg.poll(offset)
        if not isinstance(batch,list) or len(batch)>1:
            raise ValueError("Unexpected update batch")
        for raw in batch:
            guard()
            update=Update.de_json(raw,SimpleNamespace(id=a.bot))
            if not positive(update.update_id) or update.update_id<offset:
                raise ValueError("Invalid update sequence")
            offset=update.update_id+1
            message=update.effective_message
            sender=update.effective_user
            if (not message or not sender or sender.is_bot or sender.id!=a.owner
                    or message.chat.type!="private" or message.chat.id!=a.owner
                    or not a.start<=message.date.timestamp()<=clock()+1):
                raise ValueError("Unapproved update identity or date")
            text=message.text if update.message else None
            if update.message and text not in (a.silent,a.reminder+"; at start",a.question):
                raise ValueError("Unapproved message")
            if update.message and text in seen_text:
                raise ValueError("Repeated operator scenario")
            if update.message:
                seen_text.add(text)
            def dispatch(value,sig):
                route(value,sig)
                guard()
                if text==a.question:
                    answer=history(text)
                    ticket=query("SELECT attended.history_ticket(%s,%s)",(a.owner,a.bot))
                    p.deliver(ticket,{"text":answer})
                else:
                    gateway.handle(value,sig)
                if update.callback_query and update.callback_query.data.startswith("cancel/"):
                    raise RuntimeError("Owner cancelled session")
            dispatch_sdk_update(update,me,a.owner,key,dispatch,clock)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--attended",action="store_true")
    parser.add_argument("--approval")
    parser.add_argument("--profile",choices=("hardened","laptop-beta"),default="hardened")
    args=parser.parse_args()
    if not args.attended:
        return
    # Fixed read-only mounts are prepared by the attended host operator.
    root=Path("/run/attended")
    pin=args.approval or ""
    a=Approval.load((root/"manifest.json").read_bytes(),pin,(root/"revision").read_text().strip(),socket.gethostname())
    if a.profile != args.profile:
        raise ValueError("Launcher and approved profile differ")
    if (root/"STOP").exists():
        raise RuntimeError("Session is fenced")
    from dincharya.attended_runtime import verify_images, verify_wheel, telegram_tls, KERNEL_SHA, WHEEL
    verify_images(a.pg, a.app, a.n8n)
    if a.kernel_sha256 != KERNEL_SHA:
        raise ValueError("Unreviewed ephemeris")
    verify_wheel(root/WHEEL)
    tls, _ = telegram_tls()
    kernel=root/"de440s.bsp"
    with kernel.open("rb") as stream:
        if hashlib.file_digest(stream,"sha256").hexdigest()!=a.kernel_sha256:
            raise ValueError("Ephemeris mismatch")
    import psycopg
    import httpx
    stop=threading.Event()
    for sig in (signal.SIGINT,signal.SIGTERM):
        signal.signal(sig,lambda *_:stop.set())
    def blocked():
        return stop.is_set() or (root/"STOP").exists()
    with ExitStack() as stack:
        def connect(role):
            return stack.enter_context(psycopg.connect(host="db",dbname="dincharya_attended_test",
                user="attended_"+role,password=(root/(role+".key")).read_text().strip(),
                autocommit=True,connect_timeout=3,options="-c statement_timeout=3000 -c lock_timeout=1500"))
        def client(transport=None):
            return stack.enter_context(httpx.Client(timeout=4,trust_env=False,follow_redirects=False,
                                      transport=transport or httpx.HTTPTransport(retries=0,trust_env=False)))
        poll,work=connect("poller"),connect("worker")
        key=(root/"relay.key").read_text().strip()
        if len(key)<32:
            raise ValueError("Invalid signing key")
        tg=Telegram(client(telegram_transport(tls,a.profile)),(root/"bot.key").read_text().strip(),a)
        route=stack.enter_context(signed_route(key,client()))
        operate(a,pin,poll,work,tg,key,route,lambda q:historical(q,kernel),blocked)


if __name__=="__main__":
    logging.disable(logging.CRITICAL)
    try:
        main()
    except Exception as exc:
        raise SystemExit("Attended stop: "+type(exc).__name__) from None
