"""Offline approval boundary, with real Telegram SDK and a simulated wire."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from dincharya.lunar_intent import Clarify, parse_request
from dincharya.lunar_service import LunarService, envelope

ROOT = Path(__file__).resolve().parents[1]
AVAILABLE = all(importlib.util.find_spec(name) is not None for name in ("numpy", "skyfield", "erfa"))
SDK = importlib.util.find_spec("telegram") is not None
ENGLISH = 'Remind me "Family puja" on lunar Chaitra Shukla Navami, Purnimanta, ordinary, first, in 2027 at 18:00 IST'
HINDI = 'मुझे "Family puja" की तिथि चैत्र शुक्ल नवमी पूर्णिमांत सामान्य पहली २०२७ में १८:०० बजे याद दिलाओ'
HINGLISH = 'Mujhe "Family puja" Chaitra Shukla Navami tithi purnimant samanya pehli 2027 mein 18:00 baje yaad dilao'


def call(service, command, nonce="1", key="a" * 64):
    value, signature = envelope(key, command, nonce)
    return service.handle(value, signature)


def draft(service, text=ENGLISH, nonce="1"):
    return call(service, {"operation": "draft_lunar", "text": text}, nonce)


def confirm(service, review, nonce="2"):
    return call(service, {"operation": "confirm_lunar_draft", "review": review}, nonce)


def selection():
    return dict(identity=dict(version=2, convention="purnimanta", month="chaitra",
                              intercalation="ordinary", lunation_cycle=337, paksha="shukla", tithi=9),
                selected_date="2027-04-15", sunrise_dates=["2027-04-15"],
                start="2027-04-14T19:20:00+00:00", end="2027-04-15T19:20:00+00:00",
                guarded_policy="drik-delhi-pac-corroboration-v1", model_profiles=["a", "b"],
                minimum_margin_seconds=6000)


class IntentTests(unittest.TestCase):
    def test_same_structure_in_three_languages(self):
        expected = parse_request(ENGLISH)
        self.assertEqual(parse_request(HINDI), expected)
        self.assertEqual(parse_request(HINGLISH), expected)

    def test_ambiguity_and_untrusted_requests_require_clarification(self):
        for text in ("approve now", ENGLISH + " or amanta", ENGLISH + " or 19:00",
                     ENGLISH.replace("ordinary", "adhika both"), ENGLISH + " tomorrow",
                     ENGLISH.replace("Shukla Navami", "Shukla Amavasya"),
                     ENGLISH.replace("IST", "America/Chicago"), ENGLISH.replace('"Family puja"', "Family puja"),
                     ENGLISH.replace("2027", "2027-02-31"), ENGLISH + " force true"):
            with self.subTest(text=text), self.assertRaises(Clarify):
                parse_request(text)

    def test_default_disabled_and_tick_key_cannot_draft(self):
        blocked = Mock(side_effect=AssertionError("no storage access"))
        service = LunarService(blocked, blocked, blocked,
                               {"synthetic": True, "astronomy_enabled": False, "fixtures": {}},
                               "a" * 64, "b" * 64, "c" * 64)
        self.assertEqual(draft(service)["status"], "disabled")
        self.assertEqual(call(service, {"operation": "draft_lunar", "text": ENGLISH}, key="b" * 64),
                         {"status": "denied"})
        blocked.assert_not_called()

    def test_development_config_never_enables_transport(self):
        from dincharya.lunar_runtime import build_service

        cases = [
            ({"development_astronomy": "false"}, {}),
            ({"development_astronomy": True, "delivery_enabled": True}, {}),
            ({"development_astronomy": True}, {"live_approved": True}),
            ({"development_astronomy": True}, {"transport": object()}),
        ]
        with patch("dincharya.lunar_runtime.connection_factory") as factory:
            for config, options in cases:
                with self.subTest(config=config, options=options), self.assertRaises(ValueError):
                    build_service(config, **options)
            factory.assert_not_called()


@unittest.skipUnless(AVAILABLE, "optional pinned astronomy dependencies")
class ReviewTests(unittest.TestCase):
    def setUp(self):
        blocked = Mock(side_effect=AssertionError("inject scoped storage mocks"))
        self.calendar = Mock(side_effect=lambda *args: selection())
        self.service = LunarService(blocked, blocked, blocked,
                                    {"synthetic": True, "astronomy_enabled": False, "fixtures": {}},
                                    "a" * 64, "b" * 64, "c" * 64,
                                    development_calendar=self.calendar, development_profile="d" * 64)
        self.now = datetime(2026, 11, 14, tzinfo=timezone.utc).timestamp()
        self.service.development.clock = lambda: self.now
        self.owner = self.service.development.owner = Mock()
        self.calculator = self.service.development.calculator = Mock()
        self.owner.propose_series.return_value = 1
        self.owner.propose_occurrence.return_value = 2
        self.owner.inspect_request.return_value = dict(status="pending", fingerprint="test-fingerprint")
        self.owner.inspect_occurrence.return_value = dict(occurrence=dict(event_id=None, revision=0, observation=1))
        self.calculator.record_calculation.return_value = uuid4()
        self.owner.decide.return_value = dict(status="approved")

    def test_two_steps_and_duplicate_approvals_with_different_update_ids(self):
        rule = draft(self.service)
        self.assertEqual(rule["status"], "rule_preview")
        self.assertIn("2027-04-15 at 18:00 IST", rule["reply"])
        self.assertEqual(self.owner.mock_calls, [])
        self.assertEqual(self.calculator.mock_calls, [])
        occurrence = confirm(self.service, rule["review"])
        self.assertEqual(occurrence["status"], "occurrence_preview")
        self.assertEqual(self.owner.decide.call_args.args[1], 1)
        self.assertEqual(confirm(self.service, rule["review"], "3"), occurrence)
        with ThreadPoolExecutor(max_workers=2) as pool:
            one, two = pool.map(lambda n: confirm(self.service, occurrence["review"], n), ("4", "5"))
        self.assertEqual(one, two)
        self.assertEqual(one["status"], "approved")
        self.assertEqual([c.args[1] for c in self.owner.decide.call_args_list], [1, 2])
        self.assertEqual(self.owner.propose_occurrence.call_count, 1)
        self.assertFalse(self.owner.decide.call_args.kwargs.get("force", False))

    def test_tamper_cancel_and_expiry(self):
        rule = draft(self.service)["review"]
        self.assertEqual(confirm(self.service, rule + "x")["status"], "withheld")
        result = call(self.service, {"operation": "cancel_lunar_draft", "review": rule})
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(confirm(self.service, rule)["status"], "withheld")
        expired = draft(self.service)["review"]
        self.now += 1800
        self.assertEqual(confirm(self.service, expired)["status"], "withheld")
        self.assertEqual(self.owner.mock_calls, [])

    def test_stale_calculation_never_decides_occurrence(self):
        occurrence = confirm(self.service, draft(self.service)["review"])
        changed = selection()
        changed["minimum_margin_seconds"] -= 15
        self.calendar.side_effect = lambda *args: deepcopy(changed)
        self.assertEqual(confirm(self.service, occurrence["review"])["status"], "withheld")
        self.assertEqual([c.args[1] for c in self.owner.decide.call_args_list], [1])

    def test_expiry_during_recalculation_never_reaches_database(self):
        rule = draft(self.service)

        def expire(*args):
            self.now += 1800
            return selection()

        self.calendar.side_effect = expire
        self.assertEqual(confirm(self.service, rule["review"])["status"], "withheld")
        self.assertEqual(self.owner.mock_calls, [])

    def test_lost_commit_acknowledgement_retries_same_database_action(self):
        from prototypes.panchang.postgres_contract import LunarStorageError

        occurrence = confirm(self.service, draft(self.service)["review"])
        self.owner.decide.side_effect = (LunarStorageError(), {"status": "approved"})
        self.assertEqual(confirm(self.service, occurrence["review"], "5")["status"], "unavailable")
        self.assertEqual(confirm(self.service, occurrence["review"], "6")["status"], "approved")
        self.assertEqual(self.owner.decide.call_args_list[-2], self.owner.decide.call_args_list[-1])


@unittest.skipUnless(SDK, "optional Telegram SDK")
class ButtonsTests(unittest.IsolatedAsyncioTestCase):
    async def test_development_gateway_requires_separate_permission_before_bot_verification(self):
        sys.path.insert(0, str(ROOT / "telegram-gateway"))
        try:
            import lunar_acceptance
        finally:
            sys.path.pop(0)
        with (
            patch.object(lunar_acceptance, "_config", return_value={"development_astronomy": True}),
            patch.object(lunar_acceptance, "_verify_bot") as verify,
        ):
            with self.assertRaises(SystemExit):
                lunar_acceptance.run_development("not-opened")
            verify.assert_not_called()

    async def test_buttons_require_real_owner_update_and_opaque_review(self):
        from telegram import Update
        from telegram.ext import Application
        sys.path.insert(0, str(ROOT / "tests/integration"))
        try:
            from m2g_bot import OfflineBotAPI
            from lunar_handlers import register_lunar_previews
        finally:
            sys.path.pop(0)

        class Wire(OfflineBotAPI):
            def __init__(self):
                super().__init__()
                self.keyboards = []

            async def do_request(self, url, method, request_data=None, **kwargs):
                if url.endswith("/answerCallbackQuery"):
                    return 200, b'{"ok":true,"result":true}'
                if url.endswith("/sendMessage"):
                    self.keyboards.append(request_data.parameters.get("reply_markup"))
                return await super().do_request(url, method, request_data, **kwargs)

        commands = Mock()
        commands.call.side_effect = [
            dict(status="rule_preview", reply="Synthetic preview", review="R" * 24),
            dict(status="approved", reply="Recorded"),
        ]
        wire = Wire()
        app = Application.builder().token("123456:offline").request(wire).get_updates_request(Wire()).build()
        register_lunar_previews(app, 101, commands)
        await app.initialize()
        try:
            owner = {"id": 101, "first_name": "Fixture", "is_bot": False}
            message = {"message_id": 1, "date": 1, "chat": {"id": 101, "type": "private"},
                       "from": owner, "text": HINDI}
            await app.process_update(Update.de_json({"update_id": 1, "message": message}, app.bot))
            self.assertIn("Confirm", str(wire.keyboards[0]))
            callback = {"id": "10", "from": {**owner, "id": 202}, "message": message,
                        "chat_instance": "synthetic", "data": "lunar:confirm:" + "R" * 24}
            await app.process_update(Update.de_json({"update_id": 2, "callback_query": callback}, app.bot))
            self.assertEqual(commands.call.call_count, 1)
            callback["from"] = {**owner, "is_bot": True}
            await app.process_update(Update.de_json({"update_id": 3, "callback_query": callback}, app.bot))
            self.assertEqual(commands.call.call_count, 1)
            callback["from"] = owner
            await app.process_update(Update.de_json({"update_id": 4, "callback_query": callback}, app.bot))
            commands.call.assert_called_with(
                {"operation": "confirm_lunar_draft", "review": "R" * 24}, "4")
            self.assertEqual(wire.messages, ["Synthetic preview", "Recorded"])
            series = str(uuid4())
            commands.call.side_effect = None
            commands.call.return_value = dict(status="cancellation_preview", reply="Review cancellation", review="C" * 24)
            command = {**message, "text": f"/lunar_rule_cancel {series}", "entities": [
                {"type": "bot_command", "offset": 0, "length": len("/lunar_rule_cancel")},
            ]}
            await app.process_update(Update.de_json({"update_id": 5, "message": command}, app.bot))
            commands.call.assert_called_with({"operation": "cancel_lunar_annual", "series": series}, "5")
            self.assertIn("lunar:confirm:" + "C" * 24, str(wire.keyboards[-1]))
        finally:
            await app.shutdown()
