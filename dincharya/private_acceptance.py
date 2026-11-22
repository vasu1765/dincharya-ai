"""One test-bot session. All network, database and clock dependencies are injected."""
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
import re

from dincharya.reminders import DeliveryReceipt

IST = timezone(timedelta(hours=5, minutes=30), "IST")
BOT_USERNAME = "dincharya_acceptance_test_bot"
QUESTION = "/panchang 6 December 2023"
SILENT, REMINDER = "Acceptance silent", "Acceptance reminder"


class StopAcceptance(RuntimeError):
    """Abort the session with a fixed diagnostic."""


def require(condition, label):
    if not condition:
        raise StopAcceptance(label)


def positive(value):
    return type(value) is int and 0 < value < 2**63


@dataclass(frozen=True)
class Scope:
    revision: str
    start: datetime
    bot_id: int
    owner_id: int

    @classmethod
    def from_approval(cls, value, revision, now):
        require(isinstance(value, dict) and set(value) == {
            "revision", "start_ist", "bot_username", "bot_id", "owner_id", "chat_type",
            "message_cap", "reminder_cap",
        }, "Approval fields differ from the reviewed scope")
        start = datetime.fromisoformat(value["start_ist"])
        require(start.utcoffset() == IST.utcoffset(None) and start.second == start.microsecond == 0
                and time(8) <= start.time() <= time(20, 49)
                and timedelta() < start - now <= timedelta(minutes=15), "Approved start window unavailable")
        require(re.fullmatch(r"[a-f0-9]{40}", revision) and value["revision"] == revision
                and value["bot_username"] == BOT_USERNAME and value["chat_type"] == "private"
                and positive(value["bot_id"]) and positive(value["owner_id"])
                and value["bot_id"] != value["owner_id"]
                and type(value["message_cap"]) is int and value["message_cap"] == 6
                and type(value["reminder_cap"]) is int and value["reminder_cap"] == 1,
                "Approval identity, revision or message caps do not match")
        return cls(revision, start, value["bot_id"], value["owner_id"])

    def at(self, minutes):
        return self.start + timedelta(minutes=minutes)

    def commands(self):
        return (QUESTION,
                f"Schedule {SILENT} on {self.at(6):%Y-%m-%d} at {self.at(6):%H:%M}; none",
                f"Schedule {REMINDER} on {self.at(8):%Y-%m-%d} at {self.at(8):%H:%M}; at start")


class PrivateSession:
    def __init__(self, scope, telegram, commands, ledger, worker, clock, sleep):
        self.scope = scope
        self.telegram = telegram
        self.commands = commands
        self.ledger = ledger
        self.worker = worker
        self.clock = clock
        self.sleep = sleep
        self.attempts = self.reminder_attempts = 0
        self.receipts = set()
        self.offset = self.reminder_receipt = None

    def private_chat(self, value):
        return (isinstance(value, dict) and positive(value.get("id"))
                and value["id"] == self.scope.owner_id and value.get("type") == "private")

    def sender(self, value, *, bot=False):
        return (isinstance(value, dict) and positive(value.get("id"))
                and value["id"] == (self.scope.bot_id if bot else self.scope.owner_id)
                and value.get("is_bot") is bot)

    def send_chat(self, text, *, review=None, reminder=False):
        now = self.clock()
        require(self.scope.start <= now < self.scope.at(4) if not reminder else
                self.scope.at(8) <= now < self.scope.at(9), "Outbound message outside approved minute")
        require(isinstance(text, str) and 0 < len(text) <= 4096
                and self.attempts == len(self.receipts) and (not reminder or self.attempts == 5)
                and self.attempts < (6 if reminder else 5)
                and not self.reminder_attempts, "Outbound attempt budget exhausted")
        payload = {"chat_id": self.scope.owner_id, "text": text}
        if review is not None:
            payload["reply_markup"] = {"inline_keyboard": [[
                {"text": "Confirm", "callback_data": "lunar:confirm:" + review},
            ]]}
        # Reserve before I/O, including ambiguous or rejected requests.
        self.attempts += 1
        self.reminder_attempts += int(reminder)
        reply = self.telegram("sendMessage", payload)
        require(isinstance(reply, dict) and self.private_chat(reply.get("chat"))
                and self.sender(reply.get("from"), bot=True)
                and positive(reply.get("message_id")) and reply["message_id"] not in self.receipts,
                "Telegram destination or receipt could not be verified")
        self.receipts.add(reply["message_id"])
        return DeliveryReceipt(self.scope.owner_id, reply["message_id"])

    def send(self, payload):
        require(payload == {
            "event_id": self.ledger.reminder_event_id,
            "title": REMINDER,
            "occurrence_date": self.scope.at(8).date().isoformat(),
            "start_time": self.scope.at(8).strftime("%H:%M:%S"),
            "timezone": "Asia/Kolkata",
            "offset_minutes": 0,
        }, "Unexpected notification slot")
        receipt = self.send_chat(f"Reminder: {REMINDER}\n{self.scope.at(8):%Y-%m-%d %H:%M} IST", reminder=True)
        self.reminder_receipt = receipt.message_id
        return receipt

    def poll(self):
        args = {"limit": 1, "timeout": 0, "allowed_updates": ["message", "callback_query"]}
        if self.offset is not None:
            args["offset"] = self.offset
        rows = self.telegram("getUpdates", args)
        require(isinstance(rows, list) and len(rows) <= 1, "Unexpected update response")
        return rows[0] if rows else None

    def next_update(self):
        while self.clock() < self.scope.at(4):
            update = self.poll()
            if update is not None:
                ident = update.get("update_id") if isinstance(update, dict) else None
                require(positive(ident) and (self.offset is None or ident >= self.offset),
                        "Stale or malformed Telegram update")
                self.offset = ident + 1
                return update
            self.sleep(1)
        raise StopAcceptance("Owner interaction deadline passed")

    def valid_message(self, message, *, bot=False):
        return (isinstance(message, dict) and self.private_chat(message.get("chat"))
                and self.sender(message.get("from"), bot=bot)
                and positive(message.get("message_id")) and type(message.get("date")) is int
                and self.scope.start.timestamp() <= message["date"] < self.scope.at(4).timestamp()
                and message["date"] <= self.clock().timestamp() + 1)

    def expect_message(self, text):
        update = self.next_update()
        message = update.get("message")
        require(self.valid_message(message) and message.get("text") == text
                and not message.get("forward_origin") and not message.get("via_bot"),
                "Unexpected or unauthorized Telegram message")
        return update["update_id"]

    def confirm(self, review, receipt):
        update = self.next_update()
        query = update.get("callback_query")
        require(isinstance(query, dict) and self.sender(query.get("from"))
                and self.valid_message(query.get("message"), bot=True)
                and query["message"]["message_id"] == receipt.message_id
                and query.get("data") == "lunar:confirm:" + review
                and isinstance(query.get("id"), str) and 0 < len(query["id"]) <= 128,
                "Unexpected or unauthorized approval")
        require(self.telegram("answerCallbackQuery", {"callback_query_id": query["id"]}) is True,
                "Approval acknowledgement failed")
        return update["update_id"]

    def call(self, operation, key, value, ident, expected):
        require(self.scope.start <= self.clock() < self.scope.at(4),
                "Owner interaction deadline passed")
        reply = self.commands.call({"operation": operation, key: value}, str(ident))
        require(isinstance(reply, dict) and reply.get("status") == expected
                and isinstance(reply.get("reply"), str), "Signed application workflow failed")
        return reply

    def quiet_until(self, deadline):
        while self.clock() < deadline:
            require(self.poll() is None, "Unexpected extra Telegram update")
            self.sleep(1)

    def tick(self, completed):
        require(self.worker(self, self.clock) == {"status": "processed", "completed": completed},
                "Single worker changed state or delivery was not acknowledged")

    def run(self):
        require(self.clock() < self.scope.start, "Session setup missed approved start")
        self.ledger.assert_fresh()
        bot = self.telegram("getMe", {})
        require(self.sender(bot, bot=True) and bot.get("username") == BOT_USERNAME, "Dedicated bot mismatch")
        require(self.private_chat(self.telegram("getChat", {"chat_id": self.scope.owner_id})),
                "Private destination mismatch")
        webhook = self.telegram("getWebhookInfo", {})
        require(isinstance(webhook, dict) and webhook.get("url") == ""
                and type(webhook.get("pending_update_count")) is int and webhook["pending_update_count"] == 0,
                "Dedicated bot webhook or pending queue is not clear")
        require(self.poll() is None, "Dedicated bot has old updates")
        while self.clock() < self.scope.start:
            self.sleep(1)

        question, silent, reminder = self.scope.commands()
        result = self.call("historical_panchang", "text", question.partition(" ")[2],
                           self.expect_message(question), "historical_answer")
        self.ledger.assert_fresh()
        self.send_chat(result["reply"])
        for index, text in enumerate((silent, reminder), 1):
            preview = self.call("draft_recurring", "text", text, self.expect_message(text), "rule_preview")
            review = preview.get("review")
            require(isinstance(review, str) and re.fullmatch(r"[A-Za-z0-9_-]{24}", review),
                    "Missing scoped approval ticket")
            self.ledger.verify_schedule(index - 1)
            receipt = self.send_chat(preview["reply"], review=review)
            self.call("confirm_lunar_draft", "review", review, self.confirm(review, receipt), "approved")
            self.ledger.verify_schedule(index)
            self.send_chat("Appointment approved.")

        self.quiet_until(self.scope.at(6))
        require(self.clock() < self.scope.at(7), "Missed silent appointment check")
        self.tick(0)
        self.ledger.verify_delivery()
        self.quiet_until(self.scope.at(8))
        self.ledger.verify_schedule(2)
        self.tick(1)
        require(len(self.receipts) == self.attempts == 6 and self.reminder_attempts == 1,
                "Session did not produce exactly one reminder")
        self.ledger.verify_delivery(self.reminder_receipt)
        for minute in (9, 11):
            self.quiet_until(self.scope.at(minute))
            require(self.clock() < self.scope.at(minute) + timedelta(seconds=10), "Missed verification tick")
            self.tick(0)
            self.ledger.verify_delivery(self.reminder_receipt)
