from unittest import TestCase
from unittest.mock import MagicMock

from dincharya.beta_dispatch import BetaDispatcher
from dincharya.beta_observer import state
from dincharya.lunar_service import envelope


class BetaReviewTests(TestCase):
    def setUp(self):
        self.key = "x" * 32
        self.connect = MagicMock()
        self.service = BetaDispatcher(self.connect, self.key, clock=lambda: 1800000000)

    def signed(self, text):
        update = {"update_id": 1, "message": {"chat": {"id": 101, "type": "private"},
                  "from": {"id": 101, "is_bot": False}, "text": text}}
        return envelope(self.key, {"operation": "beta_update", "update": update}, "abc",
                        clock=lambda: 1800000000)

    def test_persisted_path_rejects_mixed_calendars_and_ambiguous_commands(self):
        for text in ['Schedule "lunar birthday" every year on 02-28 at 07:00',
                     "Schedule Ekadashi every Friday at 06:00",
                     "Schedule Study every Friday and every Monday at 06:00",
                     "Schedule Class daily at 06:00; none; at start"]:
            with self.subTest(text=text):
                self.assertEqual(self.service.handle(*self.signed(text)), {"status": "denied"})
        self.connect.assert_not_called()

    def test_signed_draft_checks_role_before_storage(self):
        value, sig = self.signed("Schedule Havan daily at 06:30")
        self.assertEqual(self.service.handle(value, "bad"), {"status": "denied"})
        self.connect.assert_not_called()
        conn = self.connect.return_value.__enter__.return_value
        conn.execute.return_value.fetchone.return_value = ("dincharya_beta_rehearsal", "postgres", "postgres")
        with self.assertRaises(ValueError):
            self.service.handle(value, sig)
        self.assertEqual(conn.execute.call_count, 1)

    def test_observer_rejects_stale_worker_and_backlog(self):
        sample = dict(project="dincharya-personal-beta", revision="a"*40, relay="ready", due=1,
                      sending=0, dead=0, uncertain=0, fenced_single_host=True,
                      heartbeat_age_seconds=0, oldest_due_seconds=2, oldest_sending_seconds=0)
        for edits, expected in [({"heartbeat_age_seconds":30},"worker_stalled"),
                                ({"fenced_single_host":False},"unavailable"),
                                ({"oldest_due_seconds":61},"backlog")]:
            self.assertEqual(state({**sample, **edits}, sample["revision"]), expected)
