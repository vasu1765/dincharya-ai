"""Historical Panchang through native n8n and SDK, with PostgreSQL recovery."""
import argparse
import asyncio
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from telegram import Update
from telegram.ext import Application

from m2h_development import Wire, run
from dincharya.lunar_service import connection_factory, envelope
from lunar_handlers import OrchestrationClient, register_lunar_previews
from m2h_cross_cluster import restore
from m2h_cycle5 import journey as recurring_journey
from m2h_operational_acceptance import Relay
from prototypes.panchang.astronomy import DELHI

BIRTH = ("I was born on 22 July 1995 at 14:57 in Delhi. Remind me every year on my lunar birthday at 7 AM."
         " ; Purnimanta ; first ; 60 minutes before, at start")
WEDDING = ("I was married on 7 December 2023 at 4 AM in Delhi. "
           "Schedule a yearly Hindu-calendar anniversary reminder at 8 AM. ; Amanta")


async def sdk(service, relay):
    wire = Wire()
    app = Application.builder().token("123456:offline").request(wire).get_updates_request(Wire()).build()
    register_lunar_previews(app, 101, OrchestrationClient(relay.client, relay.url, service.command_key), recurring=True)
    await app.initialize()
    try:
        for ident, text, expected in (
            (202, "What was the tithi on 6 December 2023?", None),
            (101, "What was the tithi on 6 December 2023?", "Krishna Navami"),
            (101, "७ दिसंबर २०२३ को दिल्ली में सुबह ४ बजे क्या तिथि थी?", "Krishna Dashami"),
            (101, "What was the tithi on 6 December 2023 in Mumbai?", "supported date and Delhi"),
        ):
            before = len(wire.messages)
            message = dict(date=1, chat={"id": ident, "type": "private"},
                           text=text, message_id=before+10, **{"from": {"id": ident, "first_name": "Synthetic", "is_bot": False}})
            await app.process_update(Update.de_json({"update_id": before+20, "message": message}, app.bot))
            if expected is None:
                assert len(wire.messages) == before
            else:
                assert expected in wire.messages[-1] and wire.buttons == []
    finally:
        await app.shutdown()


def historical_journey(service, relay, admin, roles, year):
    def send(operation, *, tick=False, **fields):
        value, signature = envelope(service.tick_key if tick else service.command_key,
                                    dict(operation=operation, **fields), str(uuid4()))
        return relay.forward(value, signature)

    def row_counts():
        return admin.execute(
            "SELECT (SELECT count(*) FROM public.schedule_events), (SELECT count(*) FROM lunar_private.recurring_control),"
            " (SELECT count(*) FROM lunar_private.recurring_audit)"
        ).fetchone()

    before = row_counts()
    asyncio.run(sdk(service, relay))
    assert row_counts() == before
    assert send("draft_historical_anniversary", text=BIRTH.split(" at 7 AM.")[0] + ".")["status"] == "clarify"
    preview = send("draft_historical_anniversary", text=BIRTH)
    assert preview["status"] == "rule_preview", preview
    assert "Krishna Dashami" in preview["reply"] and "Krishna Ekadashi" in preview["reply"]
    assert "07:00" in preview["reply"] and "before_and_at_start" in preview["reply"]
    assert "skipped_at_sunrise" in preview["reply"]
    assert row_counts() == before
    relay.restart_service()
    assert send("confirm_lunar_draft", review=preview["review"])["status"] == "withheld"
    fresh = send("draft_historical_anniversary", text=BIRTH)
    approved = send("confirm_lunar_draft", review=fresh["review"])
    again = send("confirm_lunar_draft", review=fresh["review"])
    assert approved["status"] == "approved" and again == approved, approved
    control = approved["control"]
    evidence, = admin.execute("SELECT request->'spec'->'historical' FROM lunar_private.recurring_audit WHERE control=%s",
                              (control,)).fetchone()
    assert evidence["event_time"] == "14:57:00" and evidence["interval"]["ordinal"] == 26
    assert evidence["months"]["purnimanta"]["month"] == "shravana"
    with connection_factory(roles["worker"])() as lease:
        lease.execute("SELECT pg_advisory_lock(20261112,4)")
        assert send("project_tick", tick=True)["status"] == "busy"
    results = send("project_tick", tick=True)
    assert results["status"] == "projected", results
    relay.restart_service()
    assert send("project_tick", tick=True)["status"] == "projected"
    days = admin.execute(
        "SELECT event_date, e.start_time::text FROM lunar_private.recurring_control c"
        " JOIN lunar_private.occurrences o ON o.series_id=c.series_id"
        " JOIN public.schedule_events e ON e.id=o.event_id WHERE c.id=%s", (control,)
    ).fetchall()
    assert not days, days
    assert admin.execute("SELECT reason FROM lunar_private.projection_review WHERE control=%s AND target_year=%s",
                         (control, year)).fetchone() == ("skipped_at_sunrise",)
    assert send("project_tick")["status"] == "denied"
    health = send("recurring_health")
    assert health["status"] == "health" and health["health"]["last_projection"], health
    wedding = send("draft_historical_anniversary", text=WEDDING)
    assert wedding["status"] == "rule_preview" and "before local sunrise" in wedding["reply"], wedding
    wedding_approval = send("confirm_lunar_draft", review=wedding["review"])
    assert wedding_approval["status"] == "approved", wedding_approval
    assert send("project_tick", tick=True)["status"] == "projected"
    relay.restart_service()
    assert send("project_tick", tick=True)["status"] == "projected"
    assert admin.execute(
        "SELECT count(*) FROM lunar_private.recurring_control c JOIN lunar_private.occurrences o ON o.series_id=c.series_id "
        "JOIN public.schedule_events e ON e.id=o.event_id WHERE c.id=%s AND e.event_date=%s AND e.start_time='08:00'",
        (wedding_approval["control"], f"{year}-11-23"),
    ).fetchone() == (1,)
    manual_preview = send("draft_historical_anniversary", text=WEDDING.replace("8 AM", "9 AM") + "; manual")
    manual = send("confirm_lunar_draft", review=manual_preview["review"])
    assert manual["status"] == "approved", manual
    assert admin.execute("SELECT mode FROM lunar_private.recurring_control WHERE id=%s",
                         (manual["control"],)).fetchone() == ("manual",)
    instant = datetime(year, 11, 23, 8, tzinfo=DELHI)

    class UncertainTransport:
        def __init__(self):
            self.attempted = []

        def send(self, payload):
            self.attempted.append(payload["title"])
            raise TimeoutError("Simulated ambiguous acceptance")

    mock = UncertainTransport()
    with connection_factory(roles["worker"])() as lease:
        lease.execute("SELECT pg_advisory_lock(20261112,3)")
        assert service.run_development_slots(mock, lambda: instant) == {"status": "busy"}
    assert not mock.attempted
    assert service.run_development_slots(mock, lambda: instant) == {"status": "uncertain"}
    restarted = relay.restart_service()
    assert restarted.run_development_slots(mock, lambda: instant + timedelta(minutes=1)) == {
        "status": "processed", "completed": 0,
    }
    assert mock.attempted == ["Lunar wedding anniversary"]
    assert len(send("recurring_health")["health"]["quarantine"]) >= 2
    print("PASS read-only SDK, historical evidence, stale and duplicate reviews, single projector, and restart")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("pg-bin", "pg-share", "ephemeris", "n8n"):
        parser.add_argument("--" + arg, required=arg != "pg-share")
    parser.add_argument("--year", type=int, required=True)
    options = parser.parse_args()

    @contextmanager
    def session(work, config):
        with ExitStack() as stack:
            yield Relay(work, config, str(Path(options.n8n).absolute()), stack)

    def journey(service, relay, admin, roles, year):
        relay.check_signatures()
        recurring_journey(service, relay, admin, roles, year)
        historical_journey(service, relay, admin, roles, year)

    def operations(work, binary, conf, login, roles, admin):
        restore(work, binary, login, roles, admin, pg_share=options.pg_share, kernel=options.ephemeris)

    run(options.pg_bin, options.ephemeris, options.pg_share, options.year,
        session=session, operations=operations, cycle5=journey, historical=True)


if __name__ == "__main__":
    main()
