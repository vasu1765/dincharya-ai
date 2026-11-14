"""Standalone isolated PostgreSQL/SDK development acceptance. Telegram HTTP is simulated."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
from uuid import UUID, uuid4

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
from prototypes.panchang.postgres_contract import LunarStorageError
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


def exercise_annual(service, restart, admin, year):
    def call(instance, operation, **fields):
        value, signature = envelope(instance.command_key, dict(operation=operation, **fields),
                                    secrets.token_urlsafe(12))
        return instance.handle(value, signature)

    def total(table):
        queries = {
            "rules": "SELECT count(*) FROM lunar_private.annual_rules",
            "events": "SELECT count(*) FROM public.schedule_events",
            "calculations": "SELECT count(*) FROM lunar_private.calculations WHERE occurrence_id IN "
                            "(SELECT o.id FROM lunar_private.occurrences o JOIN lunar_private.annual_rules a "
                            "ON a.series_id=o.series_id)",
            "deliveries": "SELECT count(*) FROM public.reminder_deliveries",
        }
        return admin.execute(queries[table]).fetchone()[0]

    def confirm(instance, preview):
        return call(instance, "confirm_lunar_draft", review=preview["review"])

    def preview(instance, series, target):
        return call(instance, "resume_lunar_annual", series=series, year=target)

    original_events = total("events")
    text = schedule_text(year, HINGLISH).replace("Family puja", "Annual fixture").replace("18:00", "20:30")
    request = call(service, "draft_lunar", text=text + " har saal")
    assert request["status"] == "rule_preview" and total("rules") == 0
    registered = confirm(service, request)
    assert registered["status"] == "annual_rule_approved", registered
    series = registered["series"]
    again = call(service, "draft_lunar", text=text + " har saal")
    assert confirm(service, again)["series"] == series and total("rules") == 1
    changed = call(service, "draft_lunar", text=text.replace(str(year), str(year + 1)) + " har saal")
    assert confirm(service, changed)["status"] == "unavailable" and total("rules") == 1
    assert total("rules") == 1 and total("events") == original_events

    discarded = preview(service, series, year)
    assert discarded["status"] == "occurrence_preview", discarded
    service = restart()
    assert confirm(service, discarded)["status"] == "withheld"
    assert series in call(service, "list_lunar_annual", after=None)["reply"]
    assert total("events") == original_events

    first = preview(service, series, year)
    assert first["occurrence"] == discarded["occurrence"]
    assert first["reply"] == discarded["reply"]
    assert confirm(service, first)["status"] == "approved"
    assert confirm(service, first)["status"] == "approved"
    assert preview(service, series, year)["status"] == "already_scheduled"
    assert total("events") == original_events + 1 and total("calculations") == 1

    cancel = call(service, "cancel_lunar_annual_occurrence", series=series, occurrence=first["occurrence"])
    assert cancel["status"] == "cancellation_preview"
    assert confirm(service, cancel)["status"] == "approved"
    assert preview(service, series, year)["status"] == "withheld"

    later = preview(service, series, year + 1)
    assert later["status"] == "occurrence_preview", later
    assert later["occurrence"] != first["occurrence"]
    assert call(service, "cancel_lunar_draft", review=later["review"])["status"] == "rejected"
    assert confirm(service, later)["status"] == "withheld"
    later = preview(service, series, year + 1)
    stop = call(service, "cancel_lunar_annual", series=series)
    assert stop["status"] == "cancellation_preview"
    assert confirm(service, later)["status"] == "approved"
    assert confirm(service, stop)["status"] == "unavailable"  # manifest changed
    assert total("events") == original_events + 2 and total("calculations") == 2

    # Independently challenge the annual year check with a different logical
    # occurrence and a compatible title/time on another date in the same year.
    saved = service.development.pending[later["review"]].data["plan"]["row"]
    forged = dict(saved["identity"], lunation_cycle=saved["identity"]["lunation_cycle"] + 1)
    selected = date.fromisoformat(saved["selected_date"]) + timedelta(days=1)
    owner, calculator = service.development.owner, service.development.calculator
    profile = service.development.profile
    alternative = UUID(str(calculator.record_calculation(
        uuid4(), UUID(series), 1, forged, profile,
        dict(status="selected", month_status="supported", date_gate="pass", kshaya=False,
             ambiguous=False, skipped=False, repeated=False, selection=selected.isoformat(),
             birth_basis="explicit_rule", repetition_policy="first",
             interval_start=f"{selected}T00:00:00+05:30", interval_end=f"{selected}T23:59:00+05:30"),
        selected)))
    rogue = owner.inspect_occurrence(alternative)["occurrence"]
    request = owner.propose_occurrence(uuid4(), alternative, "select", 1, rogue["revision"], rogue["observation"],
                                      dict(date=selected.isoformat(), title="Annual fixture", start_time="20:30"))
    reviewed = owner.inspect_request(request)
    try:
        owner.decide(uuid4(), request, "approve", reviewed["fingerprint"], reviewed=True)
    except LunarStorageError:
        pass
    else:
        raise AssertionError("Second logical occurrence was accepted in the same year")
    assert total("events") == original_events + 2

    # Run overlapping reminder refreshes twice for the second date.
    due, event_day = admin.execute(
        "SELECT (e.event_date+e.start_time) AT TIME ZONE 'Asia/Kolkata', e.event_date "
        "FROM public.schedule_events e JOIN lunar_private.occurrences o ON o.event_id=e.id WHERE o.id=%s",
        (later["occurrence"],)).fetchone()
    assert event_day.year == year + 1
    for _ in range(2):
        admin.execute("SELECT public.refresh_occurrence_reminders(%s)", (due,))
    assert admin.execute(
        "SELECT count(*),max(attempts) FROM public.reminder_deliveries d "
        "JOIN lunar_private.occurrences o ON o.event_id=d.event_id WHERE o.id=%s",
        (later["occurrence"],)).fetchone() == (1, 0)

    stop = call(service, "cancel_lunar_annual", series=series)
    state = service.development.pending[stop["review"]]
    try:
        service.development.owner.decide_annual_review(
            uuid4(), state.data["request"], "approve", state.data["fingerprint"],
            datetime.now(timezone.utc) - timedelta(seconds=1))
    except LunarStorageError:
        pass
    else:
        raise AssertionError("Expired database approval accepted")
    assert confirm(service, stop)["status"] == "approved"
    assert preview(restart(), series, year + 1)["status"] == "withheld"
    assert "cancelled" in call(service, "status_lunar_annual", series=series)["reply"]
    assert admin.execute(
        "SELECT d.status,d.attempts FROM public.reminder_deliveries d "
        "JOIN lunar_private.occurrences o ON o.event_id=d.event_id WHERE o.id=%s",
        (later["occurrence"],)).fetchone() == ("cancelled", 0)
    print("PASS annual recovery across service restart, stable identity, stale cancellation, expiry and one reminder row")


def run(pg_bin, ephemeris, pg_share=None, year=None):
    if not __debug__:
        raise ValueError("Run acceptance with assertions enabled")
    if any(key.startswith("PG") for key in os.environ):
        raise ValueError("Clear inherited PostgreSQL variables before running")
    binary = Path(pg_bin).resolve()
    year = date.today().year + 1 if year is None else year
    with tempfile.TemporaryDirectory(prefix="dincharya-m2h-") as temporary:
        work = Path(temporary)
        # Allow independent disposable runs on this host. If another process
        # wins the port after probing, PostgreSQL startup fails safely.
        from socket import socket
        with socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
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
            paths = ROOT / "database/migrations"
            migrations = sorted(paths.glob("000[1-9]_*.sql")) + sorted(paths.glob("0010_*.sql"))
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
                config = dict(
                    development_astronomy=True, public_ephemeris=ephemeris, owner_id=101, connections=roles,
                    catalog={"synthetic": True, "astronomy_enabled": False, "fixtures": {}},
                    command_key=secrets.token_hex(32), tick_key=secrets.token_hex(32),
                    review_key=secrets.token_hex(32))
                service = build_service(config)
                asyncio.run(exercise_sdk(service, admin, schedule_text(year, HINDI)))
                exercise_storage(service, admin, year)
                from dincharya.lunar_service import connection_factory
                with connection_factory(roles["calculator"])() as calculator:
                    grants = calculator.execute(
                        "SELECT has_function_privilege(session_user,"
                        "'lunar_api.list_annual_rules(uuid)','EXECUTE'), "
                        "has_function_privilege(session_user,"
                        "'lunar_api.decide_annual_review(uuid,bigint,text,text,timestamptz)','EXECUTE')"
                    ).fetchone()
                assert grants == (False, False)
                exercise_annual(service, lambda: build_service(config), admin, year)
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
