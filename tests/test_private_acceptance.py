"""Simulated Telegram I/O for the bounded session, including the production worker contract."""
from datetime import datetime, timedelta, timezone
import unittest

from dincharya.private_acceptance import (
    BOT_USERNAME, IST, PrivateSession, REMINDER, Scope, StopAcceptance,
)
from dincharya.reminders import Claim, DeliveryUncertain, process_batch


class Clock:
    def __init__(self, start):
        self.value = start - timedelta(seconds=2)

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.value += timedelta(seconds=seconds)


class RecordedTelegram:
    """Return Bot API result objects and generate only the two reviewed callback updates."""
    def __init__(self, scope, clock):
        self.scope, self.clock = scope, clock
        self.outbound, self.update_number = [], 0
        self.owner = {"id": scope.owner_id, "is_bot": False}
        self.bot = {"id": scope.bot_id, "is_bot": True, "username": BOT_USERNAME}
        self.chat = {"id": scope.owner_id, "type": "private"}
        self.fail_chat = None
        self.last_preview = None
        self.stage = 0
        self.callback_authorized = True
        self.blackout_after = None

    def __call__(self, method, payload):
        if method == "getMe":
            return self.bot
        if method == "getChat":
            return self.chat
        if method == "getWebhookInfo":
            return {"url": "", "pending_update_count": 0}
        if method == "answerCallbackQuery":
            return True
        if method == "sendMessage":
            self.outbound.append(payload)
            if self.blackout_after == len(self.outbound):
                raise TimeoutError("Simulated unconfirmed acceptance")
            message = dict(chat=self.chat, message_id=100+len(self.outbound), date=int(self.clock.now().timestamp()),
                           **{"from": self.bot})
            if len(self.outbound) == self.fail_chat:
                message["chat"] = {"id": 909, "type": "private"}
            if "reply_markup" in payload:
                self.last_preview = (payload["reply_markup"]["inline_keyboard"][0][0]["callback_data"], message)
            return message

        assert method == "getUpdates"
        if self.clock.now() < self.scope.start or self.stage >= 5:
            return []
        messages = self.scope.commands()
        if self.stage in (0, 1, 3):
            text = messages[{0: 0, 1: 1, 3: 2}[self.stage]]
            update = {"message": dict(text=text, date=int(self.clock.now().timestamp()), chat=self.chat,
                                      message_id=20+self.stage, **{"from": self.owner})}
        else:
            data, preview = self.last_preview
            actor = self.owner if self.callback_authorized else {"id": 303, "is_bot": False}
            update = {"callback_query": dict(id=str(self.stage), data=data, message=preview, **{"from": actor})}
        self.stage += 1
        self.update_number += 1
        return [dict(update_id=self.update_number, **update)]


class Application:
    def __init__(self):
        self.operations = []
        self.schedule = 0

    def call(self, command, nonce):
        self.operations.append(command["operation"])
        if command["operation"] == "historical_panchang":
            return {"status": "historical_answer", "reply": "Krishna Navami"}
        if command["operation"] == "draft_recurring":
            return {"status": "rule_preview", "reply": "Review appointment", "review": str(nonce).zfill(24)}
        assert command["operation"] == "confirm_lunar_draft"
        self.schedule += 1
        return {"status": "approved", "reply": "Approved"}


class Ledger:
    reminder_event_id = 11

    def __init__(self, scope, app):
        self.scope, self.app = scope, app
        self.state = None
        self.acks = []
        self.attempts = 0
        self.bad_slot = False

    def assert_fresh(self):
        assert self.app.schedule == 0 and self.state is None

    def verify_schedule(self, count):
        assert self.app.schedule == count

    def verify_delivery(self, message=None):
        assert self.state == ("pending" if message is None else "sent")
        assert self.acks == ([] if message is None else [message])

    def claim(self, now, limit):
        if self.state is None:
            self.state = "pending"
        if self.state != "pending" or now < self.scope.at(8):
            return []
        self.state = "sending"
        self.attempts += 1
        return [Claim(1, "test", {
            "event_id": 111 if self.bad_slot else self.reminder_event_id,
            "title": REMINDER, "occurrence_date": self.scope.at(8).date().isoformat(),
            "start_time": self.scope.at(8).strftime("%H:%M:%S"), "timezone": "Asia/Kolkata", "offset_minutes": 0,
        })]

    def finish(self, claim, outcome, now, *, receipt=None):
        self.state = outcome
        if receipt:
            assert receipt.chat_id == self.scope.owner_id
            self.acks.append(receipt.message_id)
        return True

    def worker(self, transport, clock):
        try:
            completed = process_batch(self, transport, clock, limit=1)
            return {"status": "processed", "completed": completed}
        except DeliveryUncertain:
            return {"status": "uncertain"}


class PrivateTest(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 11, 20, 11, tzinfo=IST)
        self.scope = Scope("a"*40, self.start, 202, 101)
        self.clock = Clock(self.start)
        self.telegram = RecordedTelegram(self.scope, self.clock)
        self.app = Application()
        self.ledger = Ledger(self.scope, self.app)
        self.session = PrivateSession(self.scope, self.telegram, self.app, self.ledger,
                                      self.ledger.worker, self.clock.now, self.clock.sleep)

    def assert_stopped(self, attempted):
        with self.assertRaises(StopAcceptance):
            self.session.run()
        self.assertEqual(len(self.telegram.outbound), attempted)

    def test_real_worker_contract_six_messages_exactly_one_reminder(self):
        self.session.run()
        self.assertEqual(self.app.operations, ["historical_panchang", "draft_recurring", "confirm_lunar_draft",
                                               "draft_recurring", "confirm_lunar_draft"])
        self.assertEqual([row["chat_id"] for row in self.telegram.outbound], [101]*6)
        self.assertEqual(sum(row["text"].startswith("Reminder:") for row in self.telegram.outbound), 1)
        self.assertEqual(self.ledger.acks, [106])
        self.assertEqual(self.ledger.attempts, 1)
        self.assertEqual(self.clock.now(), self.scope.at(11))

    def test_bot_or_chat_mismatch_stops_before_outbound(self):
        self.telegram.bot["username"] += "_other"
        self.assert_stopped(0)

    def test_unconfirmed_reminder_is_quarantined_without_replay(self):
        self.telegram.blackout_after = 6
        self.assert_stopped(6)
        self.assertEqual((self.ledger.state, self.ledger.attempts), ("uncertain", 1))
        self.assertEqual(self.ledger.worker(self.session, self.clock.now)["completed"], 0)
        self.assertEqual(len(self.telegram.outbound), 6)

    def test_wrong_receipt_never_replies_or_retries(self):
        self.telegram.fail_chat = 1
        self.assert_stopped(1)
        self.assertEqual(self.app.schedule, 0)

    def test_wrong_reminder_recipient_is_quarantined(self):
        self.telegram.fail_chat = 6
        self.assert_stopped(6)
        self.assertEqual((self.ledger.state, self.ledger.acks), ("uncertain", []))

    def test_missed_start_has_no_telegram_io(self):
        self.clock.value = self.scope.start
        expected = []

        def forbidden(method, payload):
            expected.append(method)
            raise AssertionError("Late startup contacted Telegram")

        self.session.telegram = forbidden
        self.assert_stopped(0)
        self.assertEqual(expected, [])

    def test_unapproved_actor_does_not_create_appointment(self):
        self.telegram.callback_authorized = False
        self.assert_stopped(2)
        self.assertEqual(self.app.schedule, 0)

    def test_unexpected_worker_payload_never_reaches_telegram(self):
        self.ledger.bad_slot = True
        self.assert_stopped(5)
        self.assertEqual(self.ledger.state, "uncertain")

    def test_approval_is_bound_to_time_revision_and_fixed_caps(self):
        approval = dict(revision=self.scope.revision, start_ist=self.start.isoformat(), bot_username=BOT_USERNAME,
                        bot_id=202, owner_id=101, chat_type="private", message_cap=6, reminder_cap=1)
        self.assertEqual(Scope.from_approval(approval, self.scope.revision, self.clock.now()), self.scope)
        for change in ({"revision": "b"*40}, {"message_cap": 7}, {"chat_type": "group"},
                       {"start_ist": self.start.astimezone(timezone.utc).isoformat()}, {"reminder_cap": True}):
            with self.subTest(change=change), self.assertRaises(StopAcceptance):
                Scope.from_approval(approval | change, self.scope.revision, self.clock.now())
        with self.assertRaises(StopAcceptance):
            Scope.from_approval(approval, self.scope.revision, self.start)
