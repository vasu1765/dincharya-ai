"""Cycle 6 against the exact previously authorized schema and daemon only."""
import argparse
import asyncio
from pathlib import Path
import sys

import httpx
import psycopg

from m2h_baseline_acceptance import BASELINE, BaselineRunner, base, service_main
from m2h_cycle5 import journey as recurring_journey
from m2h_cycle6 import historical_journey
from dincharya.lunar_runtime import build_service
from dincharya.lunar_service import envelope


class ExactRunner(BaselineRunner):
    migrations = (*BaselineRunner.migrations, "0011_synthetic_notification_slots.sql",
                  "0012_synthetic_recurring_automation.sql", "0013_synthetic_recurrence_health.sql")
    server_script = Path(__file__).name
    relay_timeout_ms = 40000

    def configure_service(self):
        super().configure_service()
        self.config.update(development_recurring=True, development_historical=True)

    async def journey(self):
        service = build_service(self.config)
        self.checkpoint("Cycle 6 signed native relay")
        with httpx.Client(transport=httpx.HTTPTransport(uds=self.n8n_socket), trust_env=False, timeout=55) as client:
            runner = self

            class Relay:
                url = "http://n8n/webhook/m2g-lunar"

                def __init__(self):
                    self.client = client

                def forward(self, value, signature):
                    response = client.post(self.url, json=value, headers={"x-dincharya-signature": signature})
                    response.raise_for_status()
                    return response.json()

                def restart_service(self):
                    runner.stop_service()
                    runner.start_service()
                    return build_service(runner.config)

            relay = Relay()
            value, signature = envelope(service.command_key, {"operation": "recurring_rules"}, "exact-cycle6")
            for _ in range(30):
                try:
                    if relay.forward(value, signature).get("status") == "listed":
                        break
                except (ValueError, httpx.HTTPError):
                    pass
                await asyncio.sleep(1)
            else:
                raise RuntimeError("Native relay unavailable")
            assert relay.forward(value, "0" * 64) == {"status": "denied"}
            role_info = self.config["connections"]
            socket_dir = role_info["owner"]["host"]
            aliases = {}
            aliases["password"] = self.env["DINCHARYA_TEST_DB_PASSWORD"]
            with psycopg.connect(host=socket_dir, dbname="dincharya_app_test", user="synthetic_test",
                                 autocommit=True, passfile="/dev/null", **aliases) as admin:
                self.checkpoint("Cycle 6 recurrence, slots and isolated restart")
                await asyncio.to_thread(recurring_journey, service, relay, admin, role_info, self.year)
                self.checkpoint("Cycle 6 historical calculation, owner approval and supervised projection")
                await asyncio.to_thread(historical_journey, service, relay, admin, role_info, self.year)
        self.checkpoint("Exact schema input integrity")
        base.require(self.baseline.read_bytes() == self.original, "Schema source changed")
        print("PASS Cycle 6 exact baseline and simulated Telegram")


def main():
    if not sys.argv[1:]:
        service_main()
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ephemeris", required=True, type=Path)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--expected-daemon-id", required=True)
    parser.add_argument("--execute-approved", action="store_true")
    args = parser.parse_args()
    if (not __debug__ or not args.execute_approved
            or args.expected_daemon_id != "44c1ef83-c50e-4ecc-8f19-4b112bc40f29"):
        parser.error("Require assertions, approved execution and the previously verified daemon")
    if not BASELINE.is_file() or BASELINE.resolve() != BASELINE:
        parser.error("Exact authorized schema unavailable")
    ExactRunner.baseline = BASELINE
    ExactRunner.kernel = str(args.ephemeris.resolve())
    ExactRunner.year = args.year
    base.Runner = ExactRunner
    base.execute(args.expected_daemon_id)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit("Cycle 6 exact baseline acceptance failed. Private runtime details suppressed.") from None
