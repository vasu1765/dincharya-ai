"""Attended disposable gateway and worker. No networking or implicit startup."""
from datetime import datetime, timezone
import hmac
import time
from uuid import UUID
from zoneinfo import ZoneInfo

from dincharya.attended_review import appointment_preview
from dincharya.beta_preview import preview
from dincharya.lunar_service import sign


def positive(value):
    return type(value) is int and 0 < value < 2**63


def identity(user, expected, bot):
    return (isinstance(user, dict) and positive(user.get("id"))
            and user["id"] == expected and user.get("is_bot") is bot)


def private(chat, owner):
    return (isinstance(chat, dict) and chat.get("type") == "private"
            and positive(chat.get("id")) and chat["id"] == owner)


class Session:
    """Use a dedicated autocommit connection, held until stopped by its supervisor."""
    def __init__(self, conn, role, owner, bot, get_me, transport):
        if role not in ("attended_worker", "attended_poller") or not conn.autocommit:
            raise ValueError("Dedicated autocommit role required")
        if not positive(owner) or not positive(bot) or owner in (101, bot):
            raise ValueError("Invalid identity pins")
        if not identity(get_me(), bot, True):
            raise ValueError("Unexpected bot")
        if conn.execute("SELECT current_database(),current_user,session_user").fetchone() != (
                "dincharya_attended_test", role, role):
            raise ValueError("Disposable scoped connection required")
        if conn.execute("SELECT attended.acquire()").fetchone() != (True,):
            raise RuntimeError("Role already owned")
        self.conn, self.owner, self.bot, self.transport = conn, owner, bot, transport

    def deliver(self, ticket, payload):
        # The preceding DB statement committed the reservation before transport.
        granted = self.conn.execute("SELECT attended.begin_send(%s,%s,%s)",
                                    (ticket, self.owner, self.bot)).fetchone()
        if granted != (True,):
            raise RuntimeError("Transport reservation fenced")
        msg = None
        try:
            reply = self.transport(chat_id=self.owner, **payload)
            result = reply["result"]
            if (reply["ok"] is True and identity(result["from"], self.bot, True)
                    and private(result["chat"], self.owner) and positive(result["message_id"])):
                msg = result["message_id"]
        finally:
            settled = self.conn.execute("SELECT attended.finish(%s,%s,%s)",
                                        (ticket, self.owner, msg)).fetchone()
        if settled != (True,):
            raise RuntimeError("Delivery fenced for inspection")

    def tick(self):
        row = self.conn.execute("SELECT * FROM attended.due(%s,%s)", (self.owner, self.bot)).fetchone()
        if row:
            self.deliver(row[1], {"text": row[0]})


class Gateway:
    def __init__(self, session, relay_key, clock=time.time):
        if not isinstance(relay_key, str) or len(relay_key) < 32:
            raise ValueError("Separate relay key required")
        self.s, self.key, self.clock = session, relay_key, clock

    def handle(self, value, signature):
        now = self.clock()
        if (not isinstance(value, dict) or set(value) != {"timestamp", "nonce", "command"}
                or type(value["timestamp"]) is not int or abs(now-value["timestamp"]) > 60
                or not isinstance(signature, str) or not signature.isascii()
                or not hmac.compare_digest(signature, sign(self.key, "command", value))):
            raise ValueError("Invalid relay envelope")
        cmd = value["command"]
        if set(cmd) != {"operation", "bot_id", "recipient", "update"} or cmd["operation"] != "attended_update":
            raise ValueError("Unexpected command")
        s = self.s
        update = cmd["update"]
        req = update["update_id"]
        if (not positive(req) or value["nonce"] != str(req) or not positive(cmd["bot_id"])
                or cmd["bot_id"] != s.bot or not positive(cmd["recipient"]) or cmd["recipient"] != s.owner):
            raise ValueError("Incorrect destination")
        if set(update) == {"update_id", "message"}:
            result = preview(update, s.owner, datetime.fromtimestamp(now, timezone.utc))
            # Validate the complete renderer contract before any database writes.
            appointment_preview({**result, "token": str(UUID(int=0))})
            activity = result["activity"]
            due = datetime.fromisoformat(activity["recurrence_rule"]["start_date"] + "T" +
                                         activity["start_time"]).replace(tzinfo=ZoneInfo("Asia/Kolkata"))
            proposal, ticket = s.conn.execute("SELECT * FROM attended.preview(%s,%s,%s,%s,%s,%s)",
                (s.owner, s.bot, req, activity["title"], due, bool(result["offset_minutes"]))).fetchone()
            payload = appointment_preview({**result, "token": str(proposal)})
        elif set(update) == {"update_id", "callback_query"}:
            cb = update["callback_query"]
            origin = cb["message"]
            if (not identity(cb["from"], s.owner, False) or not private(origin["chat"], s.owner)
                    or not identity(origin["from"], s.bot, True) or not positive(origin["message_id"])):
                raise ValueError("Invalid callback origin")
            action, raw = cb["data"].split("/")
            token = UUID(raw)
            if str(token) != raw or action not in ("confirm", "cancel"):
                raise ValueError("Invalid decision")
            accepted = action == "confirm"
            ticket, = s.conn.execute("SELECT attended.decide(%s,%s,%s,%s,%s)",
                (s.owner, s.bot, token, origin["message_id"], accepted)).fetchone()
            payload = {"text": "Appointment confirmed." if accepted else "Appointment cancelled."}
        else:
            raise ValueError("Unexpected update")
        s.deliver(ticket, payload)


def dispatch_sdk_update(update, bot_user, owner, relay_key, submit, clock=time.time):
    """Receive a PTB Update from the pinned poller and submit the minimum signed fields."""
    from dincharya.lunar_service import envelope

    def user(u):
        return {"id": u.id, "is_bot": u.is_bot}

    def chat(m):
        return {"id": m.chat.id, "type": m.chat.type}

    if not identity(user(bot_user), bot_user.id, True) or update.get_bot().id != bot_user.id:
        raise ValueError("SDK bot mismatch")
    data = {"update_id": update.update_id}
    if update.callback_query and not update.message:
        q = update.callback_query
        data["callback_query"] = {"message": {"from": user(q.message.from_user), "chat": chat(q.message),
                                              "message_id": q.message.message_id},
                                  "from": user(q.from_user), "data": q.data}
    elif update.message and not update.callback_query:
        m = update.message
        data["message"] = {"from": user(m.from_user), "chat": chat(m), "text": m.text}
    else:
        raise ValueError("Unsupported SDK update")
    cmd = {"operation": "attended_update", "bot_id": bot_user.id, "recipient": owner, "update": data}
    return submit(*envelope(relay_key, cmd, update.update_id, clock))
