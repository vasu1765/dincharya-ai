"""Standalone isolated PostgreSQL/SDK development acceptance. Telegram HTTP is simulated."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tests"), str(ROOT / "telegram-gateway")]
import httpx
import psycopg
from psycopg import sql
from telegram import Update
from telegram.ext import Application

from database.migrate import render_migrations
from dincharya.lunar_runtime import build_service
from dincharya.lunar_service import envelope
from lunar_handlers import OrchestrationClient, register_lunar_previews
from m2g_bot import OfflineBotAPI
from prototypes.panchang.guarded import development_profile
from test_lunar_development import HINDI, ENGLISH, HINGLISH


class Wire(OfflineBotAPI):
    def __init__(self):
        super().__init__()
        self.buttons = []

    async def do_request(self, url, method, request_data=None, **kwargs):
        if url.endswith("/answerCallbackQuery"):
            return 200, b'{"ok":true,"result":true}'
        if url.endswith("/sendMessage"):
            markup = request_data.parameters.get("reply_markup")
            if markup:
                keyboard = json.loads(markup) if isinstance(markup, str) else markup
                self.buttons.append(keyboard["inline_keyboard"][0])
        return await super().do_request(url, method, request_data, **kwargs)


async def exercise_sdk(service, admin, text):
    def bridge(request):
        assert urlsplit(str(request.url)).hostname == "offline.invalid"
        result = service.handle(json.loads(request.content), request.headers["x-dincharya-signature"])
        return httpx.Response(403 if result["status"] == "denied" else 200, json=result)

    def count(table):
        assert table in ("public.schedule_events", "public.schedule_change_requests", "lunar_private.series")
        return admin.execute("SELECT count(*) FROM " + table).fetchone()[0]

    wire = Wire()
    app = Application.builder().token("123456:offline").request(wire).get_updates_request(Wire()).build()
    owner = {"id": 101, "first_name": "Synthetic", "is_bot": False}
    chat = {"id": 101, "type": "private"}
    message = {"date": 1, "chat": chat, "from": owner, "text": text, "message_id": 1}

    async def send(data):
        await app.process_update(Update.de_json(data, app.bot))

    async def click(update_id, action, who=owner):
        await send({"update_id": update_id, "callback_query": {
            "id": str(update_id), "from": who, "data": action, "message": message,
            "chat_instance": "synthetic"}})

    with httpx.Client(transport=httpx.MockTransport(bridge), trust_env=False) as client:
        register_lunar_previews(app, 101, OrchestrationClient(
            client, "http://offline.invalid/lunar", service.command_key))
        await app.initialize()
        try:
            await send({"update_id": 1, "message": message})
            rule = wire.buttons[-1][0]["callback_data"]
            assert count("public.schedule_change_requests") == count("lunar_private.series") == 0
            await click(2, rule, {**owner, "id": 202})
            assert count("lunar_private.series") == 0
            await click(3, rule)
            assert count("public.schedule_events") == 0 and count("lunar_private.series") == 1
            occurrence = wire.buttons[-1][0]["callback_data"]
            await click(4, occurrence)
            await click(5, occurrence)
            assert count("public.schedule_events") == 1
            assert sum("recorded" in reply for reply in wire.messages) == 2
            await click(6, wire.buttons[-1][1]["callback_data"])
            assert count("public.schedule_events") == 1
        finally:
            await app.shutdown()
    print("PASS real Telegram SDK, both owner approvals, foreign callback denial and duplicate clicks")


def schedule_text(year, text=ENGLISH):
    return text.replace("2027", str(year)).replace("२०२७", str(year))


def exercise_storage(service, admin, year):
    def call(operation, **fields):
        value, signature = envelope(service.command_key, dict(operation=operation, **fields),
                                    secrets.token_urlsafe(12))
        return service.handle(value, signature)

    def draft(text):
        return call("draft_lunar", text=text)

    def confirm(review):
        return call("confirm_lunar_draft", review=review)

    def count():
        return admin.execute("SELECT count(*) FROM public.schedule_events").fetchone()[0]

    # Re-entering the same appointment in another language must not create a
    # second series or appointment even after all in-memory reviews are lost.
    service.development.pending.clear()
    submitted = draft(schedule_text(year, HINGLISH))
    assert confirm(submitted["review"])["status"] == "already_scheduled"
    assert count() == 1

    text = schedule_text(year).replace("Family puja", "Stale test")
    pending = confirm(draft(text)["review"])
    admin.execute("UPDATE lunar_private.occurrences SET observation=observation+1 WHERE id=%s",
                  (pending["occurrence"],))
    assert confirm(pending["review"])["status"] == "unavailable"
    assert count() == 1

    conflict = confirm(draft(text)["review"])
    assert confirm(conflict["review"])["status"] == "conflict"
    assert count() == 1

    alternate = text.replace("Stale test", "Concurrent test").replace("18:00", "19:00")
    r1, r2 = (confirm(draft(alternate)["review"]) for _ in range(2))
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda r: confirm(r["review"])["status"], (r1, r2)))
    assert sorted(outcomes) == ["approved", "unavailable"], outcomes
    assert count() == 2

    cancelled = confirm(draft(alternate.replace("19:00", "20:00"))["review"])
    assert call("cancel_lunar_draft", review=cancelled["review"])["status"] == "rejected"
    assert confirm(cancelled["review"])["status"] == "withheld"
    assert count() == 2

    # Exercise the existing reminder materializer at its due horizon. No
    # reminder transport and no real tick or Telegram message is used.
    admin.execute("SELECT public.refresh_occurrence_reminders(minimum) FROM ("
                  "SELECT min((event_date+start_time) AT TIME ZONE 'Asia/Kolkata') AS minimum "
                  "FROM public.schedule_events) AS d")
    assert admin.execute("SELECT count(*) FROM public.reminder_deliveries WHERE attempts=0").fetchone()[0] == 2
    assert service.transport is None
    print("PASS real PostgreSQL replay, stale reviews, conflicts, concurrent approvals and reminder materialization")


def run(pg_bin, ephemeris, pg_share=None, year=None):
    if not __debug__:
        raise ValueError("Run acceptance with assertions enabled")
    if any(key.startswith("PG") for key in os.environ):
        raise ValueError("Clear inherited PostgreSQL variables before running")
    binary = Path(pg_bin).resolve()
    year = date.today().year + 1 if year is None else year
    with tempfile.TemporaryDirectory(prefix="dincharya-m2h-") as temporary:
        work = Path(temporary)
        port = 55438
        bootstrap = ["-D", str(work / "data"), "-U", "synthetic_test",
                     "--auth-host=scram-sha-256", "--no-locale", "-E", "UTF8"]
        # The disposable bootstrap administrator uses a random SCRAM password.
        bootstrap_file = work / "pw"
        bootstrap_phrase = secrets.token_urlsafe(32)
        bootstrap_file.touch(mode=0o600)
        bootstrap_file.write_text(bootstrap_phrase + "\n")
        subprocess.run([binary / "initdb", *bootstrap, "--pwfile", bootstrap_file,
                        *(["-L", str(Path(pg_share).resolve())] if pg_share else [])],
                       check=True, capture_output=True)
        log = work / "postgres.log"
        conf = ("-c listen_addresses=127.0.0.1 -c unix_socket_directories='' "
                f"-p {port} -c log_statement=none -c log_min_error_statement=panic "
                "-c log_parameter_max_length=0 -c log_parameter_max_length_on_error=0")
        subprocess.run([binary / "pg_ctl", "-D", work / "data", "-l", log, "-o", conf, "start"],
                       check=True, capture_output=True)
        try:
            common = dict(host="127.0.0.1", port=port, passfile="/dev/null", connect_timeout=5)
            login = dict(common, user="synthetic_test")
            login["password"] = bootstrap_phrase
            with psycopg.connect(**login, dbname="postgres", autocommit=True) as bootstrap_conn:
                bootstrap_conn.execute("CREATE DATABASE dincharya_app_test")
            dbname = "dincharya_app_test"
            args = [binary / "psql", "-X", "-q", "-w", "-v", "ON_ERROR_STOP=1",
                    "-h", common["host"], "-p", str(port), "-U", login["user"], "-d", dbname]
            migrations = sorted((ROOT / "database/migrations").glob("000[1-9]_*.sql"))
            result = subprocess.run(args, input=Path(__file__).with_name("m2h_development_schema.sql").read_text()
                                    + "\n" + render_migrations(migrations), text=True,
                                    env={**os.environ, "PGPASSWORD": bootstrap_phrase}, capture_output=True)
            if result.returncode:
                raise RuntimeError("Synthetic migration installation failed")  # never print private configuration
            with psycopg.connect(**login, dbname=dbname, autocommit=True) as admin:
                roles = {}
                for kind, role in (("owner", "dincharya_lunar_owner"),
                                   ("calculator", "dincharya_lunar_calculator"),
                                   ("worker", "dincharya_reminder_worker")):
                    user = "m2h_fixture_" + kind
                    role_phrase = secrets.token_urlsafe(24)
                    admin.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                        sql.Identifier(user), sql.Literal(role_phrase)))
                    admin.execute(sql.SQL("GRANT {} TO {}").format(sql.Identifier(role), sql.Identifier(user)))
                    roles[kind] = dict(host=common["host"], port=port, dbname=dbname, user=user)
                    roles[kind]["password"] = role_phrase
                    if kind != "worker":
                        admin.execute("INSERT INTO lunar_private.principals "
                                      "SELECT oid,rolname,101,%s,true FROM pg_roles WHERE rolname=%s", (kind, user))
                admin.execute("INSERT INTO lunar_private.profiles(digest,specification,enabled) "
                              "SELECT lunar_private.hash(v),v,true FROM (SELECT %s::jsonb AS v) AS data",
                              (json.dumps(development_profile()),))
                service = build_service(dict(
                    development_astronomy=True, public_ephemeris=ephemeris, owner_id=101, connections=roles,
                    catalog={"synthetic": True, "astronomy_enabled": False, "fixtures": {}},
                    command_key=secrets.token_hex(32), tick_key=secrets.token_hex(32),
                    review_key=secrets.token_hex(32)))
                asyncio.run(exercise_sdk(service, admin, schedule_text(year, HINDI)))
                exercise_storage(service, admin, year)
        finally:
            subprocess.run([binary / "pg_ctl", "-D", work / "data", "-m", "fast", "stop"],
                           check=True, capture_output=True)
    print("PASS disposable PostgreSQL shutdown and cleanup")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", required=True)
    parser.add_argument("--pg-share")
    parser.add_argument("--ephemeris", required=True)
    parser.add_argument("--year", type=int, help="Future fixture year, default next civil year")
    options = parser.parse_args()
    run(options.pg_bin, options.ephemeris, options.pg_share, options.year)
