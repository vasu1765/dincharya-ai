"""Cycle 5 across real n8n, PostgreSQL 17 and simulated Telegram."""
import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from telegram import Update
from telegram.ext import Application

from m2h_development import HINDI, Wire, run, schedule_text
from m2h_operational_acceptance import Relay
from m2h_operations import run_operations
from dincharya.lunar_service import connection_factory, envelope
from dincharya.reminder_adapters import PostgresReminders
from prototypes.panchang.astronomy import DELHI
from lunar_handlers import OrchestrationClient, register_lunar_previews, send_recurring_alert


async def sdk(service, relay):
    wire = Wire()
    app = Application.builder().token("123456:offline").request(wire).get_updates_request(Wire()).build()
    register_lunar_previews(app, 101, OrchestrationClient(relay.client, relay.url, service.command_key), recurring=True)
    owner = {"id": 101, "first_name": "Synthetic", "is_bot": False}
    message = dict(date=1, chat={"id": 101, "type": "private"},
                   text="Schedule Dawn practice every day at 06:30, but don't remind me",
                   message_id=1, **{"from": owner})
    await app.initialize()
    try:
        await app.process_update(Update.de_json({"update_id": 1, "message": message}, app.bot))
        assert "automatic · none" in wire.messages[-1]
        data = wire.buttons[-1][0]["callback_data"]
        for number, ident in ((2, 202), (3, 101), (4, 101)):
            before = len(wire.messages)
            query = {"id": str(number), "from": {**owner, "id": ident}, "message": message,
                     "chat_instance": "fixture", "data": data}
            await app.process_update(Update.de_json({"update_id": number, "callback_query": query}, app.bot))
            if ident == 202:
                assert len(wire.messages) == before
            else:
                assert "Rule approved" in wire.messages[-1]
    finally:
        await app.shutdown()


async def check_alert(service, relay):
    wire = Wire()
    app = Application.builder().token("123456:offline").request(wire).get_updates_request(Wire()).build()
    ticks = OrchestrationClient(relay.client, relay.url, service.tick_key)
    await app.initialize()
    try:
        await asyncio.gather(*(send_recurring_alert(app.bot, 101, ticks) for _ in range(2)))
        assert len(wire.messages) == 1 and "withheld" in wire.messages[0]
    finally:
        await app.shutdown()


def journey(service, relay, admin, roles, year):
    def send(operation, data=None, *, tick=False):
        key = service.tick_key if tick else service.command_key
        value, signature = envelope(key, dict(operation=operation, **(data or {})), str(uuid4()))
        result = relay.forward(value, signature)
        assert result.get("status") not in ("denied", "unavailable"), (operation, result)
        return result

    def draft(content):
        result = send("draft_recurring", {"text": content})
        assert "review" in result, result
        return result["review"]

    def approve(review):
        return send("confirm_lunar_draft", {"review": review})

    def change(control, action, detail=""):
        result = send("review_recurring_change", dict(control=control, change=action, policy=detail))
        return approve(result["review"])

    asyncio.run(sdk(service, relay))
    local = datetime.now(DELHI)
    at = (local + timedelta(hours=3)).strftime("%H:%M")
    # Both logical slots become due during this controlled worker run.
    civil = approve(draft(f'Schedule "Fixture training" every day at {at}; one day before, 60 minutes before, at start'))
    ident = civil["control"]
    event, = admin.execute("SELECT event_id FROM lunar_private.recurring_control WHERE id=%s", (ident,)).fetchone()
    absent, = admin.execute("SELECT c.event_id FROM lunar_private.recurring_control c JOIN public.schedule_events e "
                            "ON e.id=c.event_id WHERE e.title='Dawn practice'").fetchone()
    elapsed = admin.execute(
        "SELECT (r.start_date+e.start_time) AT TIME ZONE e.timezone FROM public.schedule_events e "
        "JOIN public.recurrence_rules r ON r.event_id=e.id WHERE e.id=%s", (event,)).fetchone()[0]
    repo = PostgresReminders(connection_factory(roles["worker"]), notification_slots=True)
    alert_oid, slot_oid = admin.execute(
        "SELECT 'lunar_api.reserve_recurring_alert()'::regprocedure::oid,"
        "'lunar_private.notification_slot'::regclass::oid"
    ).fetchone()
    for role in ("calculator", "worker"):
        with connection_factory(roles[role])() as connection:
            assert connection.execute(
                "SELECT has_function_privilege(session_user,%s::oid,'EXECUTE'),"
                "has_table_privilege(session_user,%s::oid,'UPDATE')", (alert_oid, slot_oid)
            ).fetchone() == (False, False)
    # Avoid an artificial clock making an actual recent legacy fixture due.
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = [item for batch in pool.map(lambda _: repo.claim(elapsed, 10), range(2)) for item in batch]
    assert sorted(item.payload["offset_minutes"] for item in claims) == [0, 60, 1440]
    tomorrow, advance, start = sorted(claims, key=lambda item: -item.payload["offset_minutes"])
    assert tomorrow.payload["occurrence_date"] == (elapsed.astimezone(DELHI).date() + timedelta(days=1)).isoformat()
    assert repo.finish(tomorrow, "sent", elapsed)
    assert repo.finish(advance, "sent", elapsed)
    assert repo.finish(start, "uncertain", elapsed)
    assert not repo.claim(elapsed + timedelta(minutes=3), 10)
    assert admin.execute("SELECT count(*) FROM lunar_private.notification_slot WHERE event_id=%s", (absent,)).fetchone() == (0,)
    assert admin.execute("SELECT count(*) FROM public.reminder_deliveries WHERE event_id=ANY(%s)",
                         ([event, absent],)).fetchone() == (0,)
    assert change(ident, "notifications", "none")["status"] == "approved"
    assert admin.execute("SELECT status FROM lunar_private.notification_slot WHERE event_id=%s AND occurrence_date=%s ORDER BY offset_minutes",
                         (event, elapsed.astimezone(DELHI).date())).fetchall() == [("uncertain",), ("sent",)]
    assert change(ident, "pause")["status"] == "approved"
    assert admin.execute("SELECT enabled FROM public.schedule_events WHERE id=%s", (event,)).fetchone() == (False,)
    assert change(ident, "resume")["status"] == "approved"
    assert change(ident, "replace", "Schedule Fixture training every day at 14:50")["status"] == "approved"
    assert admin.execute("SELECT enabled,start_time::text FROM public.schedule_events WHERE id=%s",
                         (event,)).fetchone() == (True, "14:50:00")

    weekly = approve(draft("मुझे Friday study class हर शुक्रवार को १६:३० बजे"))
    update = draft("Remind me 15 minutes before my Friday study class.")
    assert approve(update)["status"] == "approved"
    assert admin.execute("SELECT offsets FROM lunar_private.recurring_control WHERE id=%s",
                         (weekly["control"],)).fetchone() == ([15],)
    leap = approve(draft("Schedule Leap day review every year on 02-29 at 22:51"))
    assert admin.execute("SELECT r.frequency,r.months,r.month_days FROM public.recurrence_rules r "
                         "JOIN lunar_private.recurring_control c ON c.event_id=r.event_id WHERE c.id=%s",
                         (leap["control"],)).fetchone() == ("yearly", [2], [29])

    lunar = schedule_text(year, HINDI).replace("Family puja", "Cycle five lunar") + " हर साल; none"
    automatic = approve(draft(lunar))
    control = automatic["control"]
    series, = admin.execute("SELECT series_id FROM lunar_private.recurring_control WHERE id=%s", (control,)).fetchone()
    assert admin.execute("SELECT count(*) FROM lunar_private.occurrences WHERE series_id=%s", (series,)).fetchone() == (0,)
    assert send("project_tick", tick=True)["status"] == "projected"
    relay.restart_service()
    assert send("project_tick", tick=True)["status"] == "projected"
    assert admin.execute("SELECT count(*) FROM lunar_private.occurrences WHERE series_id=%s AND event_id IS NOT NULL",
                         (series,)).fetchone() == (1,)

    manual = approve(draft(lunar.replace("Cycle five lunar", "Cycle five manual").replace("१८:००", "१९:००")
                           + "; manual"))
    manual_series, = admin.execute("SELECT series_id FROM lunar_private.recurring_control WHERE id=%s",
                                   (manual["control"],)).fetchone()
    assert admin.execute("SELECT count(*) FROM lunar_private.occurrences WHERE series_id=%s",
                         (manual_series,)).fetchone() == (0,)
    preview = send("resume_lunar_annual", dict(series=str(manual_series), year=year))
    assert preview["status"] == "occurrence_preview", preview
    assert approve(preview["review"])["status"] == "approved"
    assert change(manual["control"], "automatic")["status"] == "approved"
    assert send("resume_lunar_annual", dict(series=str(manual_series), year=year))["status"] == "withheld"

    # In a year without Adhika Chaitra the actual astronomical calculator
    # withholds the occurrence. Only the tick principal may reserve its notice.
    unsupported = lunar.replace("Cycle five lunar", "Cycle five withheld").replace("सामान्य", "अधिक")
    held = approve(draft(unsupported))["control"]
    assert send("project_tick", tick=True)["status"] == "projected"
    assert admin.execute("SELECT reason FROM lunar_private.projection_review WHERE control=%s AND target_year=%s",
                         (held, year)).fetchone() == ("no_occurrence_in_window",)
    assert admin.execute("SELECT count(*) FROM lunar_private.occurrences o JOIN lunar_private.recurring_control c "
                         "ON c.series_id=o.series_id WHERE c.id=%s", (held,)).fetchone() == (0,)
    asyncio.run(check_alert(service, relay))
    relay.restart_service()
    assert send("reserve_recurring_alert", tick=True)["status"] == "no_alert"
    assert "Cycle five withheld" in send("recurring_rules")["reply"]

    assert change(control, "cancel")["status"] == "approved"
    assert send("project_tick", tick=True)["status"] == "projected"
    assert admin.execute("SELECT count(*) FROM lunar_private.occurrences WHERE series_id=%s AND cancelled",
                         (series,)).fetchone() == (1,)
    print("PASS signed SDK and native relay, rolling recurrence, manual control, concurrent slots and immutable history")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("pg-bin", "pg-share", "ephemeris", "n8n"):
        parser.add_argument("--" + argument, required=argument != "pg-share")
    parser.add_argument("--year", type=int, required=True)
    options = parser.parse_args()

    @contextmanager
    def session(work, config):
        with ExitStack() as stack:
            yield Relay(work, config, str(Path(options.n8n).absolute()), stack)

    def operations(*args):
        run_operations(*args, recurring=True)

    run(options.pg_bin, options.ephemeris, options.pg_share, options.year, session=session,
        cycle5=journey, operations=operations)


if __name__ == "__main__":
    main()
