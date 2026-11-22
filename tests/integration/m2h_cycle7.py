"""Cycle 7 acceptance on disposable PostgreSQL, native n8n and simulated SDK IO."""
import argparse
import asyncio
from contextlib import ExitStack, contextmanager
from datetime import datetime, time, timedelta
from itertools import count
from pathlib import Path
from uuid import UUID, uuid4

from telegram import Update
from telegram.ext import Application

from m2h_development import HINDI, Wire, run, schedule_text
from dincharya.lunar_service import connection_factory, envelope
from dincharya.reminders import DeliveryReceipt, NotAccepted
from lunar_handlers import OrchestrationClient, register_lunar_previews
from m2h_cross_cluster import restore
from m2h_cycle5 import journey as recurring_journey
from m2h_cycle6 import historical_journey
from m2h_operational_acceptance import Relay
from prototypes.panchang.astronomy import DELHI


def request(service, relay, operation, **fields):
    body, signature = envelope(service.command_key, dict(operation=operation, **fields), str(uuid4()))
    return relay.forward(body, signature) if relay else service.handle(body, signature)


async def civil_sdk(service, relay, database, scenarios):
    mock = Wire()
    app = Application.builder().token("123456:offline").request(mock).get_updates_request(Wire()).build()
    register_lunar_previews(app, 101, OrchestrationClient(relay.client, relay.url, service.command_key), recurring=True)
    ids = count(10)
    owner = {"id": 101, "first_name": "Synthetic", "is_bot": False}
    await app.initialize()
    try:
        for title, text in scenarios:
            ident = next(ids)
            message = dict(date=1, chat={"id": 101, "type": "private"}, text=text, message_id=ident, **{"from": owner})
            update = Update.de_json({"update_id": ident, "message": message}, app.bot)
            await app.process_update(update)
            assert "Confirm" in mock.buttons[-1][0]["text"]
            await app.process_update(update)  # duplicate message, independent previews
            callbacks = [group[0]["callback_data"] for group in mock.buttons[-2:]]
            assert database.execute("SELECT count(*) FROM public.schedule_events WHERE title=%s", (title,)).fetchone() == (0,)
            for actor, data in [(202, callbacks[0]), (101, callbacks[0]), (101, callbacks[0]), (101, callbacks[1])]:
                click = next(ids)
                before = len(mock.messages)
                query = {"id": str(click), "from": {**owner, "id": actor}, "message": message,
                         "chat_instance": "fixture", "data": data}
                await app.process_update(Update.de_json({"update_id": click, "callback_query": query}, app.bot))
                if actor == 202:
                    assert len(mock.messages) == before
            assert database.execute("SELECT count(*) FROM public.schedule_events WHERE title=%s", (title,)).fetchone() == (1,)
    finally:
        await app.shutdown()


def civil_journey(service, relay, db):
    today = datetime.now(DELHI).date()
    once = today + timedelta(days=3)
    titles = ["E2E silent", "E2E daily", "E2E weekly", "E2E appointment", "E2E annual"]
    examples = [
        "Schedule E2E silent every day at 08:11; none",
        "Schedule E2E daily every day at 09:12; at start",
        "Schedule E2E weekly every Friday at 11:22; 15 minutes before",
        f"Schedule E2E appointment on {once} at 15:31; 60 minutes before, 20 minutes before, at start",
        f"Schedule E2E annual every year on {once:%m-%d} at 17:43; at start",
    ]
    asyncio.run(civil_sdk(service, relay, db, zip(titles, examples)))
    saved = db.execute(
        "SELECT e.title,c.id,c.offsets,r.frequency,c.event_id FROM lunar_private.recurring_control c "
        "JOIN public.schedule_events e ON e.id=c.event_id JOIN public.recurrence_rules r ON r.event_id=e.id "
        "WHERE e.title=ANY(%s)", (titles,)
    ).fetchall()
    by_title = {row[0]: row[1:] for row in saved}
    assert [(by_title[title][1], by_title[title][2]) for title in titles] == [
        ([], "daily"), ([0], "daily"), ([15], "weekly"), ([0, 20, 60], "once"), ([0], "yearly"),
    ]
    friday = today + timedelta(days=((4 - today.weekday()) % 7 or 7))
    due = [
        (titles[1], today + timedelta(days=1), time(9, 12), 0),
        (titles[2], friday, time(11, 7), 15),
        (titles[3], once, time(14, 31), 60),
        (titles[3], once, time(15, 11), 20),
        (titles[3], once, time(15, 31), 0),
        (titles[4], once, time(17, 43), 0),
        (titles[4], once.replace(year=once.year+1), time(17, 43), 0),
    ]
    attempts = []

    class Transport:
        def send(self, payload):
            title, offset = payload["title"], payload["offset_minutes"]
            attempts.append((title, offset))
            if (title, offset) == (titles[3], 60) and attempts.count((title, offset)) == 1:
                raise NotAccepted("Fixture confirmed it did not send")
            return DeliveryReceipt(101, 91000 + len(attempts))

    transport = Transport()
    for title, day, clock, offset in sorted(due, key=lambda row: (row[1], row[2])):
        # End one occurrence at a time. Incidental daily occurrences can also become due.
        instant = datetime.combine(day, clock, DELHI)
        before = attempts.count((title, offset))
        for _ in range(12):
            outcome = service.run_development_slots(transport, lambda: instant)
            if outcome == {"status": "processed", "completed": 0}:
                break
        increment = attempts.count((title, offset)) - before
        assert increment == 1, (title, increment)
        if (title, offset) == (titles[3], 60):
            assert service.run_development_slots(transport, lambda: instant+timedelta(seconds=29))["completed"] == 0
            service = relay.restart_service()
            assert service.run_development_slots(transport, lambda: instant+timedelta(seconds=30))["completed"] == 1
            assert attempts.count((title, offset)) == before+2
        assert db.execute("SELECT status,telegram_chat_id,telegram_message_id IS NOT NULL "
                          "FROM lunar_private.notification_slot WHERE event_id=%s AND occurrence_date=%s AND offset_minutes=%s",
                          (by_title[title][3], day, offset)).fetchone() == ("sent", 101, True)
    assert db.execute("SELECT count(*) FROM lunar_private.notification_slot WHERE event_id=%s",
                      (by_title[titles[0]][3],)).fetchone() == (0,)
    for control, *_ in by_title.values():
        p = request(service, relay, "review_recurring_change", control=str(control), change="cancel", policy="")
        assert request(service, relay, "confirm_lunar_draft", review=p["review"])["status"] == "approved"
    for label in ("01 silent routine", "02 daily receipt", "03 weekly advance receipt",
                  "04 one-off three distinct receipts", "05 two civil years and duplicate review",
                  "09 owner cancellation and preserved receipts", "12 explicit rejection backoff and restart",
                  "14 unauthorized and duplicate SDK callbacks"):
        print("PASS E" + label, flush=True)


def recovery_seed(service, relay, db, year):
    def approved(text):
        p = request(service, relay, "draft_recurring", text=text)
        a = request(service, relay, "confirm_lunar_draft", review=p["review"])
        assert a["status"] == "approved", a
        return a["control"]

    lunar = schedule_text(year, HINDI).replace("Family puja", "Restore pending lunar") + " हर साल; none"
    manual = approved(lunar.replace("१८:००", "२०:३१") + "; manual")
    automatic = approved(lunar.replace("१८:००", "२०:३३"))
    series, = db.execute("SELECT series_id FROM lunar_private.recurring_control WHERE id=%s", (manual,)).fetchone()
    p = request(service, relay, "resume_lunar_annual", series=str(series), year=year)
    assert p["status"] == "occurrence_preview", p
    old, = db.execute("SELECT id FROM public.schedule_change_requests WHERE proposed_data->>'occurrence'=%s",
                      (p["occurrence"],)).fetchone()
    auto_series, = db.execute("SELECT series_id FROM lunar_private.recurring_control WHERE id=%s", (automatic,)).fetchone()
    saved = service.owner.inspect_annual_rule(auto_series)
    spec = dict(rule=saved["series"]["rule"], year=year, title=saved["annual"]["title"], time="20:33")
    plan = service.development.recurring.plan(spec, year)
    occurrence = service.development._calculation(plan, auto_series, saved["series"]["revision"], True)
    assert db.execute("SELECT event_id FROM lunar_private.occurrences WHERE id=%s", (occurrence,)).fetchone() == (None,)

    def recovered(target, config, service):
        assert service.development.restore_epoch
        assert request(service, None, "confirm_lunar_draft", review=p["review"])["status"] == "withheld"
        fingerprint = service.owner.inspect_request(old)["fingerprint"]
        try:
            service.owner.decide(uuid4(), old, "approve", fingerprint, reviewed=True)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Restored request became approvable under the new login")
        assert target.execute("SELECT status FROM public.schedule_change_requests WHERE id=%s", (old,)).fetchone() == ("pending",)
        assert target.execute("SELECT event_id FROM lunar_private.occurrences WHERE id=%s", (occurrence,)).fetchone() == (None,)
        assert target.execute("SELECT reason FROM lunar_private.projection_review WHERE control=%s AND target_year=%s",
                              (automatic, year)).fetchone() == ("restore_review_required",)
        with connection_factory(config["connections"]["owner"])() as conn:
            assert not conn.execute("SELECT has_function_privilege(session_user,"
                                    "'lunar_api.project_before_restore_fence(uuid,integer,uuid,uuid,uuid,bigint)',"
                                    "'EXECUTE')").fetchone()[0]
        owner = config["connections"]["owner"]["user"]
        target.execute("UPDATE lunar_private.principals SET enabled=false WHERE role_name=%s", (owner,))
        try:
            assert request(service, None, "recurring_rules")["status"] == "unavailable"
        finally:
            target.execute("UPDATE lunar_private.principals SET enabled=true WHERE role_name=%s", (owner,))
        fresh = request(service, None, "resume_lunar_annual", series=str(series), year=year)
        assert fresh["status"] == "occurrence_preview" and fresh["occurrence"] == p["occurrence"], fresh
        accepted = request(service, None, "confirm_lunar_draft", review=fresh["review"])
        assert accepted["status"] == "approved", accepted
        assert request(service, None, "confirm_lunar_draft", review=fresh["review"]) == accepted
        assert target.execute("SELECT count(*) FROM lunar_private.occurrences WHERE id=%s AND event_id IS NOT NULL",
                              (UUID(fresh["occurrence"]),)).fetchone() == (1,)
        print("PASS E13 restored request fence, revoked authority, fresh review and stable occurrence", flush=True)
    return recovered


def calendar_journey(service, relay, admin):
    before = admin.execute("SELECT count(*) FROM public.schedule_events").fetchone()
    for text, status, detail in (
        ("6 December 2023 at 25:00 in Delhi", "clarify", "valid local clock"),
        ("7 December 2023 at 03:04:20 in Delhi", "withheld", "transition uncertainty"),
        ("30 June 2026 in Delhi", "historical_answer", "withheld under the 300-second date guard"),
    ):
        result = request(service, relay, "historical_panchang", text=text)
        assert result["status"] == status and detail in result["reply"], result
    assert admin.execute("SELECT count(*) FROM public.schedule_events").fetchone() == before
    print("PASS E15 native invalid clock, ambiguous instant and disputed sunrise", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pg-bin", "pg-share", "ephemeris", "n8n"):
        parser.add_argument("--" + name, required=name != "pg-share")
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--calendar-only", action="store_true")
    args = parser.parse_args()
    recovery = None

    @contextmanager
    def session(work, config):
        with ExitStack() as stack:
            yield Relay(work, config, str(Path(args.n8n).absolute()), stack)

    def journey(service, relay, admin, roles, year):
        nonlocal recovery
        calendar_journey(service, relay, admin)
        if args.calendar_only:
            return
        civil_journey(service, relay, admin)
        relay.check_signatures()
        recurring_journey(service, relay, admin, roles, year)
        historical_journey(service, relay, admin, roles, year)
        recovery = recovery_seed(service, relay, admin, year)
        print("PASS E06, E07, E08, E10, E11, E12, E14, E15 native relay and guarded journeys", flush=True)

    def operations(work, binary, conf, login, roles, admin):
        assert recovery
        restore(work, binary, login, roles, admin, pg_share=args.pg_share, kernel=args.ephemeris, recover=recovery)

    run(args.pg_bin, args.ephemeris, args.pg_share, args.year, session=session,
        operations=None if args.calendar_only else operations, cycle5=journey, historical=True, restore_fence=True)


if __name__ == "__main__":
    main()
