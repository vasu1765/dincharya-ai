"""Exact-schema Cycle 4 acceptance in the previously reviewed disposable Docker stack."""
import argparse
import asyncio
from hashlib import sha256
import json
from pathlib import Path
import sys
import threading

from m2g_runner import M2GRunner, base
from m2h_development import exercise_annual, exercise_sdk, schedule_text, HINDI
from database.migrate import render_migrations
from dincharya.lunar_http import server
from dincharya.lunar_runtime import build_service
from dincharya.lunar_service import connection_factory, envelope
from prototypes.panchang.guarded import development_profile

BASELINE = Path("/home/vasu1765/dincharya-backups/baseline-20261112T132918Z-d5V7Hf/application-schema.sql")


def service_main():
    config = json.loads(sys.stdin.readline())
    service = build_service(config)
    path = Path(config["service_socket"])
    try:
        with server(str(path), service) as instance:
            thread = threading.Thread(target=instance.serve_forever, daemon=True)
            thread.start()
            print('{"ready":true}', flush=True)
            try:
                if sys.stdin.readline().strip() != "stop":
                    raise ValueError("Expected lifecycle stop")
            finally:
                instance.shutdown()
                thread.join(timeout=5)
    finally:
        path.unlink(missing_ok=True)


class BaselineRunner(M2GRunner):
    migrations = (*M2GRunner.migrations, "0010_synthetic_annual_lunar_rules.sql")
    relay_json_denials = True
    server_script = Path(__file__).name

    def checkpoint(self, stage):
        self.current_stage = stage
        print("RUN " + stage, flush=True)

    def tests(self):
        self.checkpoint("application setup")
        try:
            super().tests()
        except Exception:
            # Fixed labels only: never stringify exception/SQL/paths or subprocess output.
            print("FAIL " + self.current_stage, flush=True)
            raise

    def configure_service(self):
        self.config.update(development_astronomy=True, public_ephemeris=self.kernel)
        self.config["catalog"]["fixtures"].clear()
        from lunar_checks import literal

        spec = literal(development_profile())
        self.app_sql(f"INSERT INTO lunar_private.profiles(digest,specification,enabled) "
                     f"SELECT lunar_private.hash({spec}),{spec},true")
        paths = [base.ROOT / "database/migrations" / name for name in self.migrations]
        statement = "SELECT version||'|'||checksum FROM public.application_migration_ledger ORDER BY version"
        expected = "\n".join(f"{path.name}|{sha256(path.read_bytes()).hexdigest()}" for path in paths)
        base.require(self.app_sql(statement) == expected, "Migration checksums differ")
        self.app_sql(render_migrations(paths))
        base.require(self.app_sql(statement) == expected, "Repeat migration changed ledger")

    async def journey(self):
        import httpx

        import psycopg
        self.checkpoint("database permissions and application construction")
        service = build_service(self.config)
        pg_socket = self.config["connections"]["owner"]["host"]
        auth = {}
        auth["password"] = self.env["DINCHARYA_TEST_DB_PASSWORD"]
        with (
            psycopg.connect(host=pg_socket, dbname="dincharya_app_test", user="synthetic_test",
                            autocommit=True, passfile="/dev/null", **auth) as admin,
            httpx.Client(transport=httpx.HTTPTransport(uds=self.n8n_socket),
                         trust_env=False, timeout=45) as client,
        ):
            self.checkpoint("scoped calculator permissions")
            with connection_factory(self.config["connections"]["calculator"])() as calculator:
                grants = calculator.execute(
                    "SELECT has_function_privilege(session_user,'lunar_api.list_annual_rules(uuid)','EXECUTE'),"
                    " has_function_privilege(session_user,"
                    "'lunar_api.decide_annual_review(uuid,bigint,text,text,timestamptz)','EXECUTE')"
                ).fetchone()
            assert grants == (False, False)
            url = "http://n8n/webhook/m2g-lunar"

            def forward(value, signature):
                response = client.post(url, json=value, headers={"x-dincharya-signature": signature})
                response.raise_for_status()
                return response.json()

            self.checkpoint("signed native n8n relay readiness")
            value, signature = envelope(service.command_key, {"operation":"list_lunar_annual","after":None}, "preflight")
            for _ in range(30):
                try:
                    if forward(value, signature)["status"] == "listed":
                        break
                except (ValueError, httpx.HTTPError):
                    pass
                await asyncio.sleep(1)
            else:
                raise RuntimeError("Signed relay did not become ready")
            assert forward(value, "0" * 64) == {"status": "denied"}
            self.checkpoint("SDK occurrence approvals")
            await exercise_sdk(service, admin, schedule_text(self.year, HINDI), url,
                               http_transport=httpx.HTTPTransport(uds=self.n8n_socket))

            def restart():
                self.stop_service()
                self.start_service()
                return build_service(self.config)

            self.checkpoint("annual approvals and restart recovery")
            exercise_annual(service, restart, admin, self.year, forward)
        self.checkpoint("schema input integrity")
        base.require(self.baseline.read_bytes() == self.original, "Schema source changed")
        print("PASS exact baseline migration, native relay annual approvals and isolated service restart")


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
    if not __debug__:
        parser.error("Run acceptance with assertions enabled")
    if not args.execute_approved or args.expected_daemon_id != "44c1ef83-c50e-4ecc-8f19-4b112bc40f29":
        parser.error("Scoped execution approval and the previously reviewed daemon are required")
    if not BASELINE.is_file() or BASELINE.resolve() != BASELINE:
        parser.error("Exact authorized schema unavailable")
    BaselineRunner.baseline = BASELINE
    BaselineRunner.kernel = str(args.ephemeris.resolve())
    BaselineRunner.year = args.year
    base.Runner = BaselineRunner
    base.execute(args.expected_daemon_id)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit("Exact baseline acceptance failed; private runtime details suppressed.") from None
