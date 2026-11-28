"""Owner-provisioned Telegram release. Import and default CLI invocation are inert."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import hashlib
import httpx
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import re
import signal
import sys
import time

from dincharya.attended_gateway import identity, positive, private
from dincharya.attended_operator import safe_exception_class, signed_route, telegram_transport
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


@contextmanager
def operation_diagnostic(method,*,report_success=True):
    if method not in {"getMe","getUpdates","sendMessage","editMessageText","answerCallbackQuery","reminder"}:
        raise ValueError("Unreviewed diagnostic operation")
    start=time.monotonic_ns()
    outcome="interrupted"
    try:
        yield
        outcome="none"
    except Exception as exc:
        outcome=safe_exception_class(exc)
        raise
    finally:
        if report_success or outcome!="none":
            try:
                print(f"operation={method} elapsed_ms={(time.monotonic_ns()-start)//1_000_000} exception={outcome}",
                      file=sys.stderr,flush=True)
            except (OSError,ValueError):
                pass


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

    def _call(self,method,body,*,operation=None):
        # Repeat only read operations at the same durable cursor. Never re-reserve
        # or replay a Telegram write, an n8n submission, or a database operation.
        delays = (0, 0.5, 1, 2) if self.approval.profile=="daily" and method in ("getMe","getUpdates") else (0,)
        for n, delay in enumerate(delays):
            deadline=time.monotonic()+delay
            while not self.stopped() and deadline>time.monotonic():
                time.sleep(min(0.2,max(0,deadline-time.monotonic())))
            if self.stopped():
                raise RuntimeError("Transport stopped")
            try:
                with operation_diagnostic(operation or method,report_success=method!="getUpdates" or n>0):
                    return self._request(method,body)
            except (httpx.ReadTimeout,httpx.ConnectTimeout,httpx.ReadError,httpx.RemoteProtocolError):
                if n+1==len(delays):
                    raise

    def _request(self,method,body):
        if self.stopped() or method not in ("getMe","getUpdates","sendMessage","editMessageText","answerCallbackQuery"):
            raise RuntimeError("Transport stopped")
        if method!="getMe" and not self.verified:
            raise RuntimeError("Bot identity unverified")
        reply=self.client.post(self.base+method,json=body,timeout=6 if method=="getUpdates" else 4)
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
        reply=self._call(method,body,operation="reminder" if kind=="reminder" else None)
        if method=="sendMessage" and body.get("reply_markup") and reply["result"].get("reply_markup")!=body["reply_markup"]:
            raise ValueError("Unexpected preview controls")
        return reply

    def __call__(self,method,body):
        return self.outbound(method,body,method)

    def reminder(self,method,body):
        if method!="sendMessage":
            raise ValueError("Invalid reminder operation")
        return self.outbound(method,body,"reminder")


def model_failure(exc,operation="intent_model"):
    try:
        print("operation="+operation+" exception="+safe_exception_class(exc),file=sys.stderr,flush=True)
    except (OSError,ValueError):
        pass


class Interpretation:
    def __init__(self,provider,reserve):
        self.provider,self.reserve=provider,reserve
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix="intent")
        self.future=None

    def offer(self,text,context):
        if self.future and not self.future.done():
            return None
        if not self.reserve():
            return None
        self.future=self.pool.submit(self.provider.infer,text,context)
        return self.future

    def close(self):
        self.pool.shutdown(wait=False,cancel_futures=True)
        self.provider.client.close()


class LiveReview(PersonalReview):
    def __init__(self,conn,key,approval,transport,lookup,anniversary=None):
        # Connections already hold both ownership locks. Both channels use the same receipt path.
        Review.__init__(self,conn,key,approval.owner,approval.bot,transport)
        self.lookup=lookup
        self.anniversary=anniversary
        self.context=None
        self.pending_intent=None
        self.daily=approval.profile=="daily"

    def calendar_request(self, *args):
        from dincharya.lunar_intent import Clarify
        try:
            return self.lookup(*args)
        except (RuntimeError,TimeoutError) as exc:
            model_failure(exc,"calendar")
            raise Clarify("Calendar calculation is temporarily unavailable.") from None

    def model_context(self,now):
        return self.context[1] if self.context and self.context[0]>now.timestamp() else None

    def model_candidate(self,update,now):
        from dincharya.beta_preview import preview
        from dincharya.feedback_intent import civil_relative, panchang_question
        from dincharya.lunar_intent import Clarify
        msg=update.get("message") or {}
        text=msg.get("text")
        if not self.daily or not isinstance(text,str) or not 1<=len(text)<=1000 or text.startswith("/") or "\n" in text:
            return None
        if self.pending_intent and self.pending_intent[0]>now.timestamp() and self.pending_intent[1][0]=="clock":
            return None
        try:
            # The complete canonical civil grammar still goes directly to validation.
            normalized=civil_relative(text,now)
            preview({**update,"message":{**msg,"text":normalized}},self.owner,now)
            return None
        except (ValueError,Clarify):
            pass
        try:
            # Supported exact lookups, not an expanding general language parser.
            q=None if re.match(r"^(?:schedule|remind)\b",text,re.I) else panchang_question(text,now,self.model_context(now))
            if q is not None:
                return None
        except (ValueError,Clarify):
            pass
        return text,self.model_context(now)

    def model_result(self,update,job,now):
        from dincharya.intent_model import as_request
        if now.timestamp()-update["message"]["date"]>60:
            return
        interpreted=None
        if job and job.done():
            try:
                interpreted=as_request(job.result(),self.model_context(now))
            except Exception as exc:
                model_failure(exc)
        if interpreted is None:
            self.reply(update["update_id"],"I couldn’t resolve that request safely. Try /help or give an explicit date and time.")
            return
        msg={**update["message"],"text":interpreted}
        value,sig=envelope(self.key,dict(operation="daily_review",recipient=self.owner,bot_id=self.bot,
                           update={**update,"message":msg}),update["update_id"],now.timestamp)
        self.handle(value,sig,now)

    def message(self,u,m,now):
        from dincharya.feedback_intent import HELP, IST, LUNAR_FOLLOW, MEDIA, civil_relative, panchang_question, parse_followup
        from dincharya.lunar_intent import Clarify
        from uuid import UUID
        request=u["update_id"]

        def reply(text):
            return self.reply(request,text)

        text=m.get("text")
        if not isinstance(text,str):
            for field,name in MEDIA.items():
                if field in m:
                    return reply(f"I can’t process {name}. Please send the request as text.")
            return super().message(u,m,now)
        if len(text)>1000 or "\n" in text:
            return reply("Send one short text request.")
        if re.match(r"^(?:schedule\s|/modify\s|मुझे\s|mujhe\s|remind me\s)",text,re.I):
            withheld=r"ek[aā]da[sś]h?[iī]|deepa[wv]ali|d[iī]p[aā]val[iī]|rama?\s*navam[iī]|janm[aā]s[hṣ]?[tṭ]am[iī]|vai(?:sh|ṣ)\w*nava|smarta|दीपावली|रामनवमी|जन्माष्टमी|एकादशी|वैष्णव|स्मार्त"
            if re.search(withheld,text,re.I):
                return reply("This observance needs a reviewed tradition and date rule.")
        if not getattr(self,"daily",True):
            return super().message(u,m,now)
        day=now.astimezone(IST).date()
        lower=text.strip().casefold()
        if lower=="/help":
            return reply(HELP)
        if lower=="/status":
            pending,uncertain,unsettled=self.conn.execute("SELECT * FROM beta.ui_status(%s,%s)",(self.owner,self.bot)).fetchone()
            return reply(f"Reminders due: {pending} · Delivery uncertain: {uncertain} · Replies need review: {unsettled}")
        if lower in ("/today","/tomorrow","/upcoming"):
            first=day+timedelta(days=lower=="/tomorrow")
            last=first+timedelta(days=6 if lower=="/upcoming" else 0)
            rows=self.conn.execute("SELECT * FROM beta.ui_upcoming(%s,%s,%s,%s)",(self.owner,self.bot,first,last)).fetchall()
            summary=f"{first:%d %b %Y}"+(f" – {last:%d %b %Y}" if first!=last else "")+" · IST"
            for name,starts in rows[:15]:
                summary+=f"\n{starts.astimezone(IST):%d %b, %H:%M} · {name}"
            return reply(summary+("\nMore appointments exist." if len(rows)>15 else "")+
                         ("\nNo upcoming appointments in this window." if not rows else ""))
        page=re.fullmatch(r"/rules(?: ([1-7]))?",lower)
        if page:
            rows=self.conn.execute("SELECT * FROM beta.ui_rules(%s,%s)",(self.owner,self.bot)).fetchall()
            n=int(page[1] or 1)
            visible=rows[(n-1)*15:n*15]
            if not visible:
                return reply("No active rules on this page.")
            lines=[f"Active rules · page {n}/{(len(rows)+14)//15} · {len(rows)} shown in total"]
            lines.extend(f"{name} · {freq} · {uid}" for uid,name,freq in visible)
            if n*15<len(rows):
                lines.append(f"Next: /rules {n+1}")
            return reply("\n".join(lines))
        if lower.startswith("/modify "):
            try:
                key=UUID(lower.split()[1])
            except (ValueError,IndexError):
                return reply("Use a rule ID from /rules.")
            if self.conn.execute("SELECT beta.ui_is_lunar(%s,%s,%s)",(self.owner,self.bot,key)).fetchone()==(True,):
                return reply("Cancel the existing lunar rule with confirmation, then request a reviewed replacement.")

        # Structured context stays only in this single owner's process and expires after 15 minutes.
        if self.context and self.context[0]<=now.timestamp():
            self.context=None
        if self.pending_intent and self.pending_intent[0]<=now.timestamp():
            self.pending_intent=None
        remembered=self.context[1] if self.context else None
        try:
            if remembered and self.pending_intent and self.pending_intent[1][0]=="clock" and re.fullmatch(
                    r"(?:at )?\d{1,2}(?::\d{2})?(?:\s*[ap]m)?",lower):
                period=self.pending_intent[1][1]
                self.pending_intent=None
                text=f"Remind me {period} at {re.sub(r'^at ', '', lower)}"
            incomplete=re.fullmatch(r"remind me (?:when this occurs? )?(this year|every year)[.?!]?",lower)
            if incomplete and remembered and remembered.get("basis"):
                self.pending_intent=(now.timestamp()+900,("clock",incomplete[1]))
                return reply("What time in IST should I use? For example, at 7 AM.")
            history_prefix=re.match(r"^(?:i was (?:born|married)|birth(?:day)?|wedding|marriage)\b",lower)
            if history_prefix and LUNAR_FOLLOW.search(text):
                from dincharya.historical_intent import anniversary_text
                this_year=bool(re.search(r"\bthis year\b",text,re.I))
                event,clock,mode,convention,repeat,offsets,title,_=anniversary_text(
                    re.sub(r"\bthis year\b","every year",text,count=1,flags=re.I) if this_year else text)
                if mode!="automatic":
                    raise Clarify("Request this year for one reviewed lunar date.")
                if event.instant()>=now:
                    raise Clarify("Give one earlier Delhi event time.")
                result=self.calendar_request(f"{event.day.isoformat()} at {event.clock.isoformat()} Delhi",False)
                basis=result["context"]["basis"].get(convention) if result.get("context") else None
                if not basis:
                    raise Clarify("The event’s Māsa, Paksha or Tithi needs review.")
                return self.lunar_preview(u,dict(title=title,annual=not this_year,clock=clock,offsets=offsets,
                    rule={**basis,"repeated":repeat},year=day.year),now)
            if LUNAR_FOLLOW.search(text) and (re.search(r"tithi|this year|when this",text,re.I)
                    or (remembered and lower.startswith("remind me"))):
                return self.lunar_preview(u,parse_followup(text,remembered,now),now)
            if not re.match(r"^(?:schedule|remind|/modify|/cancel|मुझे|mujhe)\b",text,re.I):
                q=panchang_question(text,now,remembered)
                if q is not None:
                    self.context=None
                    self.pending_intent=None
                    result=self.calendar_request(q,text.startswith("/details "))
                    if isinstance(result,str):
                        return reply(result)
                    answer=reply(result["text"])
                    if result.get("context"):
                        self.context=(now.timestamp()+900,result["context"])
                    return answer
            normalized=civil_relative(text,now)
        except Clarify as e:
            return reply(str(e))
        return super().message({**u,"message":{**m,"text":normalized}},{**m,"text":normalized},now)

    def lunar_preview(self,u,intent,now):
        from dincharya.daily_review import IST, label_for_rule, when
        from dincharya.lunar_intent import Clarify
        if self.anniversary is None:
            raise Clarify("This lunar date is awaiting validation.")
        clock=intent["clock"]
        rule=intent["rule"]
        if clock.second or not intent["title"] or not intent["title"].isprintable():
            raise Clarify("Use a short plain title and a time to the minute.")
        candidate=None
        first=intent["year"]
        for year in range(first,first+(2 if intent["annual"] else 1)):
            try:
                row=self.anniversary(rule,year)
            except (RuntimeError,TimeoutError) as exc:
                model_failure(exc,"calendar")
                raise Clarify("Lunar calculation is temporarily unavailable. No schedule was created.") from None
            if row:
                day=date.fromisoformat(row["day"])
                when_at=datetime.combine(day,clock,IST)
                if now<when_at<=now+timedelta(days=400):
                    candidate=row
                    break
        if not candidate:
            raise Clarify("No future Delhi date in the approved evidence window. Skipped, uncertain and unverified dates stay unscheduled.")
        p,t=self.conn.execute("SELECT * FROM beta.ui_draft_lunar(%s,%s,%s,%s,%s,%s,%s::integer[],%s,%s,%s,%s,%s)",
            (self.owner,self.bot,u["update_id"],intent["title"],day,clock,intent["offsets"],candidate["rule"],
             candidate["month_kind"],intent["annual"],rule["birth_basis"],rule["repeated"])).fetchone()
        mode="Every year · only independently validated Delhi dates" if intent["annual"] else "This year only"
        offsets=", ".join("at start" if n==0 else f"{n} min before" for n in intent["offsets"]) or "none"
        body=dict(chat_id=self.owner,text=f"{intent['title']}\n{label_for_rule(rule)}\n{mode}\n"
                  f"{when(day,clock)}\nSource interpretation: {rule['birth_basis']} · repeated tithi: {rule['repeated']}\n"
                  f"Reminders: {offsets}",
                  reply_markup={"inline_keyboard":[[{"text":v.title(),"callback_data":f"{v}/{p}"}
                                                       for v in ("confirm","cancel")]]})
        self.emit(t,"sendMessage",body)
        self.pending_intent=(now.timestamp()+900,("approval",p))
        return "preview"

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


def dispatch(review,tg,update,now,relay,interpret=None):
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
    if interpret is not None and callback is None:
        candidate=review.model_candidate(update,now)
        if candidate is not None:
            return interpret.offer(*candidate),update,time.monotonic()+22
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
    from dincharya.personal_history import anniversary, lookup
    from dincharya.intent_model import configured
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
            connection=dict(host="db",dbname="dincharya_personal_candidate",user=role,autocommit=True,
                            connect_timeout=3,options="-c statement_timeout=5000 -c lock_timeout=2000")
            connection["password"]=(root/(role+".key")).read_text().strip()
            return stack.enter_context(psycopg.connect(**connection))
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
        review=LiveReview(gateway,key,a,tg,
            lambda q,d:lookup(q,d,root/"de440s.bsp",root/WHEEL,structured=a.profile=="daily"),
            lambda rule,year:anniversary(rule,year,root/"de440s.bsp",root/WHEEL))
        route=stack.enter_context(signed_route(key,client(httpx.HTTPTransport(retries=0,trust_env=False))))
        if worker.execute("SELECT beta.recording_ready()").fetchone()!=(True,):
            raise RuntimeError("Release requires inspection")
        gate("start")
        tg.verify()
        interpret,pending=None,None
        if a.profile=="daily":
            try:
                provider=configured(root,tls)
            except (OSError,ValueError,TypeError) as exc:
                model_failure(exc)
                provider=None
            if provider is not None:
                def reserve():
                    p=provider.profile
                    if p.provider=="ollama":
                        return True
                    return gateway.execute("SELECT beta.reserve_model(%s,%s,%s,%s,%s,%s)",
                        (a.owner,a.bot,pin,p.max_calls,p.max_micro_usd,p.per_call_micro_usd)).fetchone()==(True,)
                interpret=Interpretation(provider,reserve)
                stack.callback(interpret.close)
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
            if pending is not None:
                job, original, deadline=pending
                if job is not None and not job.done() and time.monotonic()<deadline:
                    time.sleep(0.2)
                    continue
                if stopped():
                    return
                review.model_result(original,job,datetime.now(timezone.utc))
                gate("ack",original["update_id"]+1)
                pending=None
                continue
            batch=tg.poll(offset)
            if stopped():
                return
            if not isinstance(batch,list) or len(batch)>1:
                raise ValueError("Unexpected polling batch")
            for update in batch:
                if not positive(update.get("update_id")) or update["update_id"]<offset:
                    raise ValueError("Invalid update sequence")
                pending=dispatch(review,tg,update,datetime.now(timezone.utc),route,interpret)
                if pending is None:
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
            raise SystemExit("Daily release stopped: "+safe_exception_class(exc)) from None
