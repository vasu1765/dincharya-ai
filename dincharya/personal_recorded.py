"""Personal candidate dispatcher. Its default transport is an in-memory Telegram transcript."""
from collections import deque
from uuid import UUID
import re

from dincharya.daily_review import Review
from dincharya.lunar_service import envelope


class Recorder:
    def __init__(self,owner,bot,allocate=None):
        self.allocate=allocate
        self.owner,self.bot=owner,bot
        self.messages={}
        self.calls=[] if allocate is None else deque(maxlen=16)

    def __call__(self,method,body):
        if method=="answerCallbackQuery":
            if set(body)!={"callback_query_id","text"}:
                raise ValueError("Unexpected callback notice")
            result=True
        else:
            if method not in ("sendMessage","editMessageText") or body.get("chat_id")!=self.owner:
                raise ValueError("Unexpected recording destination")
            num=(self.allocate() if self.allocate else len(self.messages)+1) if method=="sendMessage" else body["message_id"]
            if method=="editMessageText" and self.allocate is None and num not in self.messages:
                raise ValueError("Missing recorded original")
            result=dict(message_id=num,chat=dict(id=self.owner,type="private"),
                        text=body["text"],reply_markup=body.get("reply_markup",{}),
                        **{"from":dict(id=self.bot,is_bot=True)})
            if self.allocate is None:
                self.messages[num]=result
        self.calls.append(method)
        return {"ok":True,"result":result}


class PersonalReview(Review):
    database_identity=("dincharya_personal_candidate","personal_gateway","personal_gateway")

    def __init__(self,conn,key,owner,bot,recorder,lookup):
        if not isinstance(recorder,Recorder):
            raise ValueError("Recording transport required")
        super().__init__(conn,key,owner,bot,recorder)
        if conn.execute("SELECT beta.acquire()").fetchone()!=(True,):
            raise RuntimeError("Gateway fenced")
        self.lookup=lookup

    def message(self,u,m,now):
        text=m.get("text")
        if isinstance(text,str) and re.match(r"^(?:/modify\s|schedule\s|मुझे\s|mujhe\s|remind me\s)",text,re.I):
            if re.search(r"ram[a ]*navami|janma?shtami|janmashtami|smarta|vai(?:sh|ṣ)\w*nava|vaishnava|राम\s*नवमी|जन्माष्टमी|स्मार्त|वैष्णव",text,re.I):
                return self.reply(u["update_id"],"This observance needs a reviewed tradition and date rule.")
        if text=="/rules":
            rows=self.conn.execute("SELECT * FROM beta.ui_rules(%s,%s)",(self.owner,self.bot)).fetchall()
            result="Active rules (up to 25)\n"+"\n".join(f"{name} · {freq} · {uid}" for uid,name,freq in rows)
            return self.reply(u["update_id"],result if rows else "No active rules.")
        if isinstance(text,str) and len(text)<=1000:
            parts=text.split(maxsplit=2)
            if parts and parts[0] in ("/modify","/cancel"):
                try:
                    target=UUID(parts[1])
                    if str(target)!=parts[1]:
                        raise ValueError()
                except (IndexError,ValueError):
                    return self.reply(u["update_id"],"Use a rule ID from /rules.")
                if parts[0]=="/cancel" and len(parts)==2:
                    row=self.change_draft(u,target,"cancel",None,None,None,None,None)
                    if not row:
                        return self.reply(u["update_id"],"This rule is no longer active.")
                    p,ticket,label=row
                    self.emit(ticket,"sendMessage",dict(chat_id=self.owner,text=f"Cancel future occurrences of {label}?",
                        reply_markup={"inline_keyboard":[[{"text":"Confirm","callback_data":"confirm/"+str(p)},
                                                         {"text":"Keep rule","callback_data":"cancel/"+str(p)}]]}))
                    return "preview"
                if parts[0]=="/modify" and len(parts)==3:
                    changed={**m,"text":parts[2]}
                    return super().message({**u,"message":changed,"change_target":target},changed,now)
                return self.reply(u["update_id"],"Use /cancel ID or /modify ID followed by a complete schedule.")
            detailed=text.startswith("/details ")
            q=text[9:] if detailed else text
            if detailed or re.search(r"tithi|panchang|lunar details|तिथि|पंचांग",q,re.I):
                return self.reply(u["update_id"],self.lookup(q,detailed))
        return super().message(u,m,now)

    def change_draft(self,u,target,op,title,freq,day,clock,offsets):
        return self.conn.execute("SELECT * FROM beta.ui_change_draft(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::integer[])",
            (self.owner,self.bot,u["update_id"],target,op,title,freq,day,clock,offsets)).fetchone()

    def reserve_preview(self,u,title,freq,day,clock,offsets):
        if "change_target" not in u:
            return super().reserve_preview(u,title,freq,day,clock,offsets)
        row=self.change_draft(u,u["change_target"],"replace",title,freq,day,clock,offsets)
        return (row[0],row[1],f"Replace {row[2]} with {title}?") if row else None


def dispatch_recorded(review,update,now):
    # Derive local change metadata exclusively after signature verification.
    if not isinstance(update,dict) or set(update) not in ({"update_id","message"},{"update_id","callback_query"}):
        return "denied"
    value,sig=envelope(review.key,dict(operation="daily_review",bot_id=review.bot,
        recipient=review.owner,update=update),update["update_id"],lambda:now.timestamp())
    return review.handle(value,sig,now)
