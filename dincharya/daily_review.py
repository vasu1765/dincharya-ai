"""Isolated daily UX candidate. Only injected recording transport; no poll or HTTP client."""
from datetime import datetime
import hmac
from uuid import UUID
from zoneinfo import ZoneInfo

from dincharya.attended_gateway import identity, positive, private
from dincharya.beta_preview import preview
from dincharya.lunar_service import sign

IST = ZoneInfo("Asia/Kolkata")
STATUS = {"kept":"Change declined · original kept","removed":"Future schedule cancelled","replaced":"Replacement confirmed", "active":"Confirmed", "cancelled":"Cancelled", "expired":"Preview expired",
          "paused":"Paused", "conflict":"Time already occupied"}
NOTICE = {"kept":"Original rule kept.","removed":"Future occurrences already cancelled.","replaced":"Replacement already confirmed.", "active":"Already confirmed. To change it, request a new review.",
          "cancelled":"Already cancelled.", "expired":"This preview expired. Request a fresh one.",
          "paused":"This schedule is paused.", "conflict":"Please choose another time."}


def when(day, clock):
    return f"{day:%d %b %Y} · {clock:%I:%M %p} IST"


def historical_reply(question, calendar, *, detailed=False):
    from dincharya.historical_panchang import HistoricalPanchang, historical_text, label
    event = historical_text(question)
    reader = HistoricalPanchang(calendar)
    value = reader.read(event)
    if detailed:
        return reader.display(event,value)
    return concise(event,value,label,devanagari=any("\u0900"<=c<="\u097f" for c in question))


def concise(event,value,label,*,devanagari=False):
    if devanagari:
        names=("प्रतिपदा","द्वितीया","तृतीया","चतुर्थी","पञ्चमी","षष्ठी","सप्तमी","अष्टमी","नवमी",
               "दशमी","एकादशी","द्वादशी","त्रयोदशी","चतुर्दशी")
        def label(n):
            name="पूर्णिमा" if n==15 else "अमावस्या" if n==30 else names[(n-1)%15]
            return ("शुक्ल" if n<=15 else "कृष्ण")+" "+name
        sunrise=value["sunrise"]
        lines=[f"{event.day:%d %b %Y} · नई दिल्ली (IST)",
               "सूर्योदय पर: "+label(sunrise) if sunrise else "सूर्योदय के पास तिथि परिवर्तन है। तिथि अनिश्चित है।"]
        if event.clock is not None:
            lines.append(f"{event.clock:%H:%M} पर: {label(value['interval']['ordinal'])}")
        for row in value["transitions"]:
            at=datetime.fromisoformat(row["at"]).astimezone(IST)
            lines.append(f"{label(row['ordinal'])} · आरम्भ {at:%H:%M}")
        return "\n".join(lines)
    sunrise = value["sunrise"]
    lines=[f"{event.day:%d %b %Y} · New Delhi (IST)",
           f"At sunrise: {label(sunrise)}" if sunrise else "Sunrise tithi withheld: the transition is too close to sunrise."]
    if event.clock is not None:
        lines.append(f"At {event.clock:%I:%M %p}: {label(value['interval']['ordinal'])}")
    for row in value["transitions"]:
        at=datetime.fromisoformat(row["at"]).astimezone(IST)
        lines.append(f"{label(row['ordinal'])} begins at {at:%I:%M %p}.")
    return "\n".join(lines)


class Review:
    database_identity=("dincharya_beta_rehearsal","daily_gateway","daily_gateway")

    def __init__(self,conn,key,owner,bot,record,calendar=None):
        if (not conn.autocommit or not positive(owner) or not positive(bot) or owner==bot
                or not isinstance(key,str) or len(key)<32 or conn.execute(
                    "SELECT current_database(),current_user,session_user").fetchone()!=self.database_identity):
            raise ValueError("Scoped rehearsal connection required")
        self.conn,self.key,self.owner,self.bot,self.record,self.calendar=conn,key,owner,bot,record,calendar

    def emit(self,ticket,method,body):
        if ticket is None:
            return
        valid=False
        message=None
        try:
            response=self.record(method,body)
            result=response["result"]
            if method=="answerCallbackQuery":
                valid=response["ok"] is True and result is True
            else:
                message=result["message_id"]
                valid=(response["ok"] is True and positive(message) and private(result["chat"],self.owner)
                       and identity(result["from"],self.bot,True) and result.get("text")==body["text"])
                if method=="editMessageText":
                    valid=valid and message==body["message_id"] and not (result.get("reply_markup") or {}).get("inline_keyboard")
        finally:
            settled=self.conn.execute("SELECT beta.ui_finish(%s,%s,%s,%s,%s)",
                (self.owner,self.bot,ticket,valid,message if valid else None)).fetchone()[0]
        if not settled:
            raise RuntimeError("UI operation requires inspection")

    def reply(self,request,text):
        ticket,=self.conn.execute("SELECT beta.ui_reply(%s,%s,%s)",(self.owner,self.bot,request)).fetchone()
        self.emit(ticket,"sendMessage",dict(chat_id=self.owner,text=text))
        return text

    def handle(self,envelope,signature,now):
        if (now.utcoffset() is None or not isinstance(envelope,dict) or set(envelope)!={"command","timestamp","nonce"}
                or type(envelope["timestamp"]) is not int or abs(now.timestamp()-envelope["timestamp"])>60
                or not isinstance(signature,str) or not signature.isascii()
                or not hmac.compare_digest(sign(self.key,"command",envelope),signature)):
            return "denied"
        cmd=envelope["command"]
        if not isinstance(cmd,dict) or set(cmd)!={"operation","bot_id","recipient","update"} or cmd["operation"]!="daily_review":
            return "denied"
        u=cmd["update"]
        if not isinstance(u,dict) or set(u) not in ({"update_id","message"},{"update_id","callback_query"}) or not positive(u.get("update_id")) or envelope["nonce"]!=str(u["update_id"]):
            return "denied"
        if any(not positive(cmd[k]) or cmd[k]!=v for k,v in (("bot_id",self.bot),("recipient",self.owner))):
            return "denied"
        if set(u)=={"update_id","callback_query"}:
            return self.callback(u["callback_query"])
        m=u.get("message")
        if not isinstance(m,dict) or not private(m.get("chat"),self.owner) or not identity(m.get("from"),self.owner,False):
            return "denied"
        if type(m.get("date")) is not int or not 0<=now.timestamp()-m["date"]<=60:
            return "That message expired. Please send a fresh request."
        return self.message(u,m,now)

    def message(self,u,m,now):
        def reply(text):
            return self.reply(u["update_id"],text)
        text=m.get("text")
        if not isinstance(text,str) or len(text)>1000:
            return reply("Please send one scheduling request or Panchang question.")
        from dincharya.lunar_intent import Clarify
        if self.calendar is not None:
            from dincharya.historical_panchang import historical_route
            from prototypes.panchang.astronomy import Unsupported
            detailed=text.startswith("/details ")
            q=text[9:] if detailed else text
            if historical_route(q)=="historical_panchang":
                try:
                    answer=historical_reply(q,self.calendar,detailed=detailed)
                except (Clarify,Unsupported):
                    return reply("Please check the date, time and Delhi location.")
                return reply(answer)
        try:
            v=preview(u,self.owner,now)
        except (Clarify,ValueError):
            return reply("Please give an activity, date and time, or ask a Delhi tithi question.")
        a=v["activity"]
        rule=a["recurrence_rule"]
        freq=rule["frequency"]
        if freq not in ("once","daily","weekly","yearly") or rule.get("interval_count")!=1:
            return reply("This recurrence needs a separate review.")
        title=a["title"]
        if not isinstance(title,str) or not title.isprintable() or not 1<=len(title)<=80:
            return reply("Please give a short activity name.")
        day=datetime.fromisoformat(rule["start_date"]).date()
        clock=datetime.strptime(a["start_time"],"%H:%M").time()
        offsets=v["offset_minutes"]
        recurrence={"once":"Once","daily":"Daily","weekly":f"Every {day:%A}","yearly":f"Every year on {day:%d %b}"}[freq]
        row=self.reserve_preview(u,title,freq,day,clock,offsets)
        if row is None:
            return reply("That rule is no longer active. Use /rules for the current list.")
        p,ticket,heading=row
        notes=", ".join("at start" if x==0 else f"{x} min before" for x in offsets) or "none"
        self.emit(ticket,"sendMessage",dict(chat_id=self.owner,text=f"{heading}\n{recurrence} · {when(day,clock)}\nReminders: {notes}",
            reply_markup={"inline_keyboard":[[{"text":x.title(),"callback_data":f"{x}/{p}"} for x in ("confirm","cancel")]]}))
        return "preview"

    def reserve_preview(self,u,title,freq,day,clock,offsets):
        p,t=self.conn.execute("SELECT * FROM beta.ui_draft(%s,%s,%s,%s,%s,%s,%s,%s::integer[])",
            (self.owner,self.bot,u["update_id"],title,freq,day,clock,offsets)).fetchone()
        return p,t,title

    def callback(self,q):
        if not isinstance(q,dict) or not identity(q.get("from"),self.owner,False):
            return "denied"
        m=q.get("message")
        if (not isinstance(m,dict) or not private(m.get("chat"),self.owner) or not identity(m.get("from"),self.bot,True)
                or not positive(m.get("message_id")) or not isinstance(q.get("id"),str) or not 0<len(q["id"])<=128):
            return "denied"
        try:
            action,raw=q["data"].split("/")
            token=UUID(raw)
            if str(token)!=raw or action not in ("confirm","cancel"):
                return "denied"
        except (ValueError,KeyError,AttributeError):
            return "denied"
        row=self.conn.execute("SELECT * FROM beta.ui_decide(%s,%s,%s,%s,%s)",
            (self.owner,self.bot,token,m["message_id"],action=="confirm")).fetchone()
        if row is None:
            return "denied"
        status,method,ticket,title,day,clock=row
        if method=="editMessageText":
            body=dict(chat_id=self.owner,message_id=m["message_id"],text=f"{STATUS[status]} · {title}\n{when(day,clock)}",
                      reply_markup={"inline_keyboard":[]})
        elif method=="answerCallbackQuery":
            body=dict(callback_query_id=q["id"],text=NOTICE[status])
        else:
            raise RuntimeError("Unexpected UI operation")
        self.emit(ticket,method,body)
        return NOTICE[status]
