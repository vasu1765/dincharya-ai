"""Synthetic PostgreSQL outage, delivery and restore checks."""
from datetime import datetime, timedelta, timezone
import os
import subprocess

import psycopg

from dincharya.lunar_service import connection_factory
from dincharya.reminder_adapters import PostgresReminders, TelegramReminders
from dincharya.reminders import DeliveryUncertain, process_batch
from prototypes.panchang.astronomy import DELHI


def run_operations(work, binary, conf, login, roles, admin):
    repository = PostgresReminders(connection_factory(roles["worker"]), restricted_worker=True)
    start = datetime.now(timezone.utc).replace(microsecond=0)
    calls = []

    class Response:
        def __init__(self, code, body):
            self.status_code = code
            self.body = body

        def json(self):
            return self.body

    def wire(url, *, json):
        assert url.endswith("/sendMessage") and json["chat_id"] == 101
        case = json["text"].splitlines()[0].split()[-1]
        calls.append(case)
        if case == "uncertain":
            raise TimeoutError("Simulated loss after transport acceptance")
        if case == "retry" and calls.count(case) == 1:
            return Response(400, {"ok": False, "error_code": 400})
        return Response(200, {"ok": True, "result": {"chat": {"id": 101}, "message_id": len(calls)}})

    def tick(instant):
        return process_batch(repository, TelegramReminders(wire, "123456:offline", 101),
                             lambda: instant, limit=1)

    def seed(case, due):
        local = due.astimezone(DELHI)
        event = admin.execute(
            "INSERT INTO public.schedule_events(title,event_date,start_time,timezone,recurrence) "
            "VALUES(%s,%s,%s,'Asia/Kolkata','once') RETURNING id",
            (f"Cycle4 fixture {case}", local.date(), local.time())).fetchone()[0]
        admin.execute(
            "INSERT INTO public.recurrence_rules(event_id,calendar_system,frequency,interval_count,start_date,rule_options) "
            "VALUES(%s,'gregorian','once',1,%s,%s::jsonb) ON CONFLICT(event_id) DO UPDATE SET rule_options=excluded.rule_options",
            (event, local.date(), '{"managed_by":"m2d"}'))
        return event

    def ledger(connection, event):
        return connection.execute(
            "SELECT status,attempts,telegram_message_id IS NOT NULL FROM public.reminder_deliveries WHERE event_id=%s",
            (event,)).fetchall()

    retry = seed("retry", start - timedelta(minutes=1))
    assert tick(start) == 0 and ledger(admin, retry) == [("failed", 1, False)]
    assert tick(start + timedelta(seconds=29)) == 0
    assert tick(start + timedelta(seconds=30)) == 1
    assert ledger(admin, retry) == [("sent", 2, True)]

    step = start + timedelta(minutes=2)
    uncertain = seed("uncertain", step)
    try:
        tick(step)
    except DeliveryUncertain:
        pass
    else:
        raise AssertionError("Ambiguous transport acceptance was not reported")

    step += timedelta(minutes=2)
    lease = seed("lease", step)
    claim, = repository.claim(step, 1)
    outage = seed("outage", step + timedelta(minutes=1))
    late = seed("late", step - timedelta(hours=7))
    postgres = [binary / "pg_ctl", "-D", work / "data"]
    subprocess.run([*postgres, "-m", "fast", "stop"], check=True, capture_output=True, timeout=30)
    try:
        try:
            tick(step)
        except psycopg.OperationalError:
            pass
        else:
            raise AssertionError("Stopped database did not fail closed")
        assert calls == ["retry", "retry", "uncertain"]
    finally:
        subprocess.run([*postgres, "-l", work / "postgres.log", "-o", conf, "start"],
                       check=True, capture_output=True, timeout=30)

    with psycopg.connect(**login, dbname="dincharya_app_test", autocommit=True) as resumed:
        step += timedelta(minutes=3)
        assert tick(step) == 1
        assert not repository.finish(claim, "sent", step)
        assert tick(step) == 0
        expected = {retry: [("sent", 2, True)], outage: [("sent", 1, True)],
                    uncertain: [("uncertain", 1, False)], lease: [("uncertain", 1, False)], late: []}
        assert all(ledger(resumed, event) == rows for event, rows in expected.items())
        assert calls == ["retry", "retry", "uncertain", "outage"]
        annual_rows = resumed.execute("SELECT to_jsonb(a) FROM lunar_private.annual_rules a ORDER BY series_id").fetchall()
        audit_rows = resumed.execute("SELECT to_jsonb(a) FROM lunar_private.actions a ORDER BY id").fetchall()

    db_env = {**os.environ, "PGPASSWORD": login["password"]}
    args = ["-h", login["host"], "-p", str(login["port"]), "-U", login["user"], "-w"]
    dump = work / "fixture.dump"
    subprocess.run([binary / "pg_dump", *args, "-Fc", "-f", dump, "dincharya_app_test"],
                   check=True, env=db_env, capture_output=True, timeout=30)
    admin.close()
    with psycopg.connect(**login, dbname="postgres", autocommit=True) as bootstrap:
        bootstrap.execute("CREATE DATABASE dincharya_restore_test")
        subprocess.run([binary / "pg_restore", *args, "-d", "dincharya_restore_test",
                        "--single-transaction", "--exit-on-error", dump],
                       check=True, env=db_env, capture_output=True, timeout=30)
        # Keep the original disposable database as a comparison, and give the
        # restored copy the exact name required by the restricted worker API.
        bootstrap.execute("ALTER DATABASE dincharya_app_test RENAME TO dincharya_original_test")
        bootstrap.execute("ALTER DATABASE dincharya_restore_test RENAME TO dincharya_app_test")

    with psycopg.connect(**login, dbname="dincharya_app_test", autocommit=True) as restored:
        assert restored.execute("SELECT to_jsonb(a) FROM lunar_private.annual_rules a ORDER BY series_id").fetchall() == annual_rows
        assert restored.execute("SELECT to_jsonb(a) FROM lunar_private.actions a ORDER BY id").fetchall() == audit_rows
        assert all(ledger(restored, event) == rows for event, rows in expected.items())
        assert tick(step + timedelta(minutes=5)) == 0
        assert calls == ["retry", "retry", "uncertain", "outage"]
    print("PASS PostgreSQL outage, retry, expired lease quarantine, synthetic dump/restore and no redelivery")
