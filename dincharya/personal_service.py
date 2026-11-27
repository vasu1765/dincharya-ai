"""Foreground recorded daily service. Starts only with --recorded; contains no Telegram client."""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import selectors
import os
import signal
import sys
import time

from dincharya.attended_gateway import identity,positive,private
from dincharya.daily_review import IST
from dincharya.personal_recorded import PersonalReview,Recorder,dispatch_recorded


def deliver_due(worker,record,owner,bot):
    item=worker.execute("SELECT * FROM beta.recording_claim()").fetchone()
    if item is None:
        return
    slot,ticket,recipient,title,starts=item
    msg=None
    try:
        if recipient!=owner:
            raise ValueError("Worker recipient mismatch")
        body={"chat_id":owner,"text":f"{title} · {starts.astimezone(IST):%d %b %Y, %I:%M %p} IST"}
        reply=record("sendMessage",body)
        result=reply["result"]
        if (reply["ok"] is True and identity(result.get("from"),bot,True) and private(result.get("chat"),owner)
                and positive(result.get("message_id")) and result.get("text")==body["text"]):
            msg=result["message_id"]
    finally:
        ok=worker.execute("SELECT beta.finish(%s,%s,%s,%s,%s)",
            (slot,ticket,"sent" if msg else "uncertain",owner if msg else None,msg)).fetchone()[0]
    if not ok or msg is None:
        raise RuntimeError("Delivery fenced for inspection")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--recorded",action="store_true")
    p.add_argument("--root",type=Path)
    args=p.parse_args()
    if not args.recorded:
        return
    from dincharya.attended_runtime import WHEEL
    from dincharya.personal_history import lookup
    import psycopg
    root=args.root
    if root is None or not root.is_absolute() or (root/"STOP").exists():
        raise ValueError("Recording root missing or fenced")
    cfg=json.loads((root/"recording.json").read_bytes())
    owner,bot=cfg["owner"],cfg["bot"]
    key=secrets.token_hex(32)
    stopping=False
    def stop(*_):
        nonlocal stopping
        stopping=True
    for sig in (signal.SIGTERM,signal.SIGINT):
        signal.signal(sig,stop)
    with ExitStack() as stack:
        def connect(role):
            return stack.enter_context(psycopg.connect(host="db",dbname="dincharya_personal_candidate",
                user=role,password=(root/(role+".key")).read_text().strip(),autocommit=True,connect_timeout=3,
                options="-c statement_timeout=5000 -c lock_timeout=2000"))
        gateway,worker=connect("personal_gateway"),connect("personal_worker")
        from dincharya.daily_sdk import RecordedSDK
        record=RecordedSDK(owner,bot,
            lambda:gateway.execute("SELECT beta.recorded_id()").fetchone()[0],
            lambda:gateway.execute("SELECT beta.reserve_recording(%s,%s)",(owner,bot)).fetchone()[0],
            lambda:stopping or (root/"STOP").exists())
        stack.callback(record.close)
        review=PersonalReview(gateway,key,owner,bot,record,
                              lambda q,d:lookup(q,d,root/"de440s.bsp",root/WHEEL))
        if worker.execute("SELECT beta.acquire()").fetchone()!=(True,):
            raise RuntimeError("Worker fenced")
        reader=stack.enter_context(selectors.DefaultSelector())
        reader.register(sys.stdin,selectors.EVENT_READ)
        pending=b""
        projection=0
        while not stopping and not (root/"STOP").exists():
            if worker.execute("SELECT beta.recording_ready()").fetchone()!=(True,):
                raise RuntimeError("Recording requires inspection")
            if time.monotonic()>=projection:
                worker.execute("SELECT beta.roll_forward()")
                projection=time.monotonic()+3600
            deliver_due(worker,record,owner,bot)
            if b"\n" not in pending:
                if not reader.select(1):
                    continue
                chunk=os.read(sys.stdin.fileno(),8192)
                if not chunk:
                    return
                pending+=chunk
            if len(pending)>32768:
                raise ValueError("Oversized recorded input")
            if b"\n" in pending:
                line,pending=pending.split(b"\n",1)
                if stopping or (root/"STOP").exists():
                    return
                dispatch_recorded(review,record.poll_one(json.loads(line)),datetime.now(timezone.utc))
                print("processed",flush=True)


if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit("Recorded service stopped: "+type(exc).__name__) from None
