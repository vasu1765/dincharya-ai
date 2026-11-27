"""Offline Telegram HTTP transcript through the real operator loop and scoped DB."""
from pathlib import Path
import hashlib
import json
import os
import secrets
import sys
import time
from contextlib import ExitStack

import httpx
import psycopg

from beta_relay_journey import DenialMismatch, install, wait_for_webhook
from dincharya import attended_operator as operator
from dincharya.attended_operator import Approval
from unittest.mock import patch

def main(mark):
    from dincharya.attended_runtime import telegram_tls, verify_images
    import runpy
    mark("telegram_tls")
    context, ca_sha = telegram_tls()
    runpy.run_path("/candidate/tests/test_attended_trust.py")["exercise_tls"](context)
    print("PASS immutable image CA sha256="+ca_sha, flush=True)
    mark("approval_manifest")
    raw=Path("/candidate/manifest.json").read_bytes()
    pin=hashlib.sha256(raw).hexdigest()
    a=Approval.load(raw,pin,os.environ["REV"],"operator-fixture")
    verify_images(a.pg,a.app,a.n8n)
    bot=dict(id=a.bot,is_bot=True,first_name="Test",username=a.bot_username)
    owner=dict(id=a.owner,is_bot=False,first_name="Fixture")
    chat=dict(id=a.owner,type="private")
    replies=[]
    seq=0
    def respond(request):
        nonlocal seq
        method=request.url.path.split("/")[-1]
        payload=json.loads(request.content)
        if method=="getMe":
            mark("approval_consumed")
            result=bot
        elif method=="sendMessage":
            assert len(replies)<6
            mark(("historical_reply", "silent_preview", "silent_confirmation",
                  "reminder_preview", "reminder_confirmation", "reminder_delivery")[len(replies)])
            assert payload.pop("chat_id")==a.owner
            result=dict(message_id=50+len(replies),date=int(time.time()),chat=chat,**{"from":bot},**payload)
            replies.append(result)
        elif method=="getUpdates":
            seq+=1
            if seq<=5:
                mark(("historical_start", "silent_preview_start", "silent_confirmation_start",
                      "reminder_preview_start", "reminder_confirmation_start")[seq-1])
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
    mark("runtime_startup")
    with ExitStack() as stack:
        client=stack.enter_context(httpx.Client(timeout=5,trust_env=False))
        install(mark)
        # Only the Telegram transport is recorded. Run the actual CLI, file mounts,
        # identity/DB checks, signed relay receiver, TLS factory and child calculator.
        real_transport=httpx.HTTPTransport
        def transport(**kwargs):
            import ssl
            if isinstance(kwargs.get("verify"),ssl.SSLContext):
                assert kwargs["retries"]==0 and kwargs["trust_env"] is False
                return httpx.MockTransport(respond)
            return real_transport(**kwargs)
        original=operator.operate
        def ready(*args,**kwargs):
            wait_for_webhook(client,mark)
            return original(*args,**kwargs)
        stack.enter_context(patch.object(httpx,"HTTPTransport",side_effect=transport))
        stack.enter_context(patch.object(operator,"operate",side_effect=ready))
        stack.enter_context(patch.object(sys,"argv",["operator","--attended","--approval",pin]))
        operator.main()
        mark("operator_receipts")
        assert len(replies)==6 and "2023-12-06" in replies[0]["text"] and "Drik Delhi primary" in replies[0]["text"] and replies[-1]["text"]=="Reminder"
        count=len(replies)
        mark("consumed_approval_restart_rejection")
        try:
            operator.main()
        except RuntimeError as exc:
            assert str(exc)=="Disposable approval absent or consumed"
        else:
            raise AssertionError("Operator resumed a consumed session")
        assert len(replies)==count
    print("PASS operator six recorded sends via native relay and fenced restart")
def run(journey=main):
    step = "startup"

    def mark(name):
        nonlocal step
        step = name
        print(f"OPERATOR_STEP step={name}", flush=True)

    try:
        journey(mark)
    except Exception as exc:
        kind = next((cls.__name__ for cls in (
            httpx.HTTPStatusError, httpx.ReadTimeout, httpx.ConnectError,
            httpx.RequestError, DenialMismatch, psycopg.Error, AssertionError,
            KeyError, TypeError, ValueError, RuntimeError, ImportError,
        ) if isinstance(exc, cls)), "Exception")
        status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else 0
        frame = exc.__traceback__
        while frame.tb_next:
            frame = frame.tb_next
        filename = Path(frame.tb_frame.f_code.co_filename).name
        site = filename if filename in {"operator_path.py", "attended_operator.py",
                                        "attended_gateway.py", "astronomy.py",
                                        "historical_panchang.py", "beta_relay_journey.py"} else "external"
        location = f" site={site}:{frame.tb_lineno}" if site != "external" else ""
        print(f"OPERATOR_FAIL step={step} class={kind} http={status}{location}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__=="__main__":
    sys.exit(run())
