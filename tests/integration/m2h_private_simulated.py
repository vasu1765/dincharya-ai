"""Targeted bounded-wrapper journey with real PostgreSQL/n8n and simulated Bot API."""
import argparse
from contextlib import ExitStack, contextmanager
from datetime import datetime, time, timedelta
from pathlib import Path

from m2h_development import run
from m2h_operational_acceptance import Relay
from m2h_private_telegram import AcceptanceLedger, BotAPI
from test_private_acceptance import Clock, RecordedTelegram
from dincharya.private_acceptance import IST, PrivateSession, Scope, StopAcceptance
from lunar_handlers import OrchestrationClient


class RecordedHTTP:
    def __init__(self, telegram, fail_reminder):
        self.telegram, self.fail_reminder = telegram, fail_reminder

    def post(self, url, *, json):
        from httpx import Response

        method = url.rsplit("/", 1)[-1]
        if self.fail_reminder and method == "sendMessage" and json["text"].startswith("Reminder:"):
            self.telegram.outbound.append(json)
            return Response(429, json={"ok": False, "error_code": 429})
        return Response(200, json={"ok": True, "result": self.telegram(method, json)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pg-bin", "pg-share", "ephemeris", "n8n"):
        parser.add_argument("--" + name, required=name != "pg-share")
    parser.add_argument("--fail-reminder", action="store_true")
    args = parser.parse_args()

    @contextmanager
    def session(work, config):
        with ExitStack() as stack:
            yield Relay(work, config, str(Path(args.n8n).absolute()), stack)

    def journey(service, relay, admin, roles, year):
        tomorrow = datetime.now(IST).date() + timedelta(days=1)
        start = datetime.combine(tomorrow, time(11), IST)
        scope = Scope("a"*40, start, 202, 101)
        clock = Clock(start)
        transcript = RecordedTelegram(scope, clock)
        bot = BotAPI(RecordedHTTP(transcript, args.fail_reminder), "recorded")
        ledger = AcceptanceLedger(admin, scope)
        flow = PrivateSession(scope, bot, OrchestrationClient(relay.client, relay.url, service.command_key),
                              ledger, service.run_development_slots, clock.now, clock.sleep)
        if args.fail_reminder:
            try:
                flow.run()
            except StopAcceptance:
                pass
            else:
                raise AssertionError("Rate-limited delivery did not stop")
            assert admin.execute(
                "SELECT status, attempts, telegram_message_id FROM lunar_private.notification_slot"
            ).fetchall() == [("uncertain", 1, None)]
            assert service.run_development_slots(flow, clock.now) == {"status": "processed", "completed": 0}
            print("PASS bounded native relay, Telegram 429 quarantine and no resend", flush=True)
        else:
            flow.run()
            assert flow.reminder_receipt == 106
            ledger.verify_delivery(106)
            print("PASS bounded native relay, six Bot API chat attempts, one receipt, zero silent sends", flush=True)
        assert len(transcript.outbound) == 6

    run(args.pg_bin, args.ephemeris, args.pg_share, session=session, cycle5=journey,
        historical=True, restore_fence=True)


if __name__ == "__main__":
    main()
