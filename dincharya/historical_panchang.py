"""Read-only Delhi Panchang and historical-event recurrence proposals."""
from dataclasses import asdict
from datetime import date, datetime, time, timedelta
import hashlib
import json

from dincharya.lunar_intent import Clarify
from dincharya.historical_intent import (HistoricalInput, PROFILE, anniversary_text, civil_start,
                                         historical_route, historical_text, label, local_instant, local_text)
from prototypes.panchang.astronomy import Astronomy, DELHI, Unsupported
from prototypes.panchang.guarded import (MODELS, REFERENCE_PATH, delhi_observations,
                                         development_profile, edge_window, publisher_endpoints)
from prototypes.panchang.recurrence import DATE_GUARD_SECONDS, LunarRule, RecurrenceResearch

VERSION = "delhi-historical-v1"


class HistoricalPanchang:
    def __init__(self, calendar):
        self.calendar = calendar

    def read(self, event):
        if event.profile != PROFILE or self.calendar.specification != development_profile():
            raise Unsupported("Historical location or calculation profile requires review")
        reference_bytes = REFERENCE_PATH.with_name("historical-references.json").read_bytes()
        primary = [r for r in json.loads(reference_bytes)["observations"] if r["use"] == "delhi_civil_and_geocentric"]
        with Astronomy(self.calendar.kernel) as astronomy:
            observed = dict(delhi_observations())
            observed.update({r["day"]: r["sunrise_ordinal"] for r in primary})
            endpoints = publisher_endpoints() + tuple((r["entering"], r["transition"]) for r in primary)
            start = civil_start(event.day)
            end = civil_start(event.day + timedelta(days=1))
            dawns = sorted(astronomy.sunrise(event.day, model) for model in MODELS)
            sunrise_ordinals = {astronomy.tithi_at(dawn) for dawn in dawns}
            transitions = astronomy.transitions(start, end)
            sunrise = next(iter(sunrise_ordinals)) if len(sunrise_ordinals) == 1 else None
            if sunrise is not None and observed.get(event.day.isoformat(), sunrise) != sunrise:
                sunrise = None
            for row in transitions:
                low, high = edge_window(datetime.fromisoformat(row["at"]), row["ordinal"], endpoints)
                if low <= dawns[-1] + timedelta(seconds=DATE_GUARD_SECONDS) and high >= dawns[0] - timedelta(seconds=DATE_GUARD_SECONDS):
                    sunrise = None
            profile = dict(version=VERSION, selection=self.calendar.specification,
                           historical_references=hashlib.sha256(reference_bytes).hexdigest())
            provenance = hashlib.sha256(json.dumps(profile, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            result = dict(sunrise=sunrise, dawns=dawns, transitions=transitions,
                          day_start=astronomy.tithi_at(start), provenance=provenance)
            if sunrise is not None:
                naming = RecurrenceResearch(astronomy)
                result["sunrise_months"] = {}
                for convention in ("purnimanta","amanta"):
                    try:
                        labels = [naming.label_at(dawn,sunrise,convention) for dawn in dawns]
                        result["sunrise_months"][convention] = labels[0] if labels[0]==labels[1] and labels[0]["supported"] else None
                    except Unsupported:
                        result["sunrise_months"][convention] = None
            if event.clock is not None:
                result.update(self.instant_details(astronomy, event.instant(), endpoints))
            return result

    @staticmethod
    def instant_details(astronomy, instant, endpoints):
        interval = astronomy.tithi_interval(instant)
        for key, ordinal in (("start", interval["ordinal"]), ("end", interval["ordinal"] % 30 + 1)):
            edge = datetime.fromisoformat(interval[key])
            low, high = edge_window(edge, ordinal, endpoints)
            if min(low, edge-timedelta(seconds=.1)) <= instant <= max(high, edge+timedelta(seconds=.1)):
                raise Unsupported("Event instant falls inside a tithi transition uncertainty interval")
        naming = RecurrenceResearch(astronomy, month_edge_seconds=.1)
        months = {}
        for convention in ("amanta", "purnimanta"):
            try:
                month = naming.label_at(instant, interval["ordinal"], convention)
                months[convention] = month if month["supported"] else None
            except Unsupported:
                months[convention] = None
        return dict(instant=instant, interval=interval, months=months)

    @staticmethod
    def display(event, value):
        lines = [f"{event.day} · {PROFILE.name} ({PROFILE.latitude}° N, {PROFILE.longitude}° E) · {PROFILE.timezone}"]
        sunrise = value["sunrise"]
        lines.append(f"At local sunrise · {label(sunrise)}" if sunrise else "At local sunrise · withheld under the 300-second date guard")
        from dincharya.daily_review import month_text
        lines.append("Sunrise "+month_text(value.get("sunrise_months",{})))
        if event.clock is None:
            lines.append(f"At the start of the civil date · {label(value['day_start'])}")
            lines.append("Computed transitions (local time, minute display) ·")
            lines.extend(f'{local_text(datetime.fromisoformat(row["at"]))} → {label(row["ordinal"])}'
                         for row in value["transitions"])
            if not value["transitions"]:
                lines[-1] = "No computed transition during this local civil date."
        else:
            instant = value["instant"]
            interval = value["interval"]
            lines.append(f'At event time {instant.astimezone(DELHI).isoformat()} · {label(interval["ordinal"])}')
            if instant < min(value["dawns"]):
                lines.append("This event was before local sunrise. An anniversary would use the event instant.")
            elif instant < max(value["dawns"]):
                lines.append("The event falls between the two local sunrise estimates.")
            lines.append(f'Computed interval, local minute display · {local_text(datetime.fromisoformat(interval["start"]))}'
                         f' to {local_text(datetime.fromisoformat(interval["end"]))}')
            lines.append("Event "+month_text(value["months"]))
        lines.append("Apparent geocentric tithi · Amanta/Purnimanta month conventions · Drik Delhi primary, IMD PAC secondary")
        lines.append(f'{VERSION} · Skyfield/DE440s · profile {value["provenance"][:12]}')
        return "\n".join(lines)

    def anniversary(self, recurring, text):
        event, reminder, mode, convention, repeated, offsets, title, purpose = anniversary_text(text)
        now = datetime.fromtimestamp(recurring.dev.clock(), DELHI)
        if event.instant() >= now:
            raise Clarify("Use a historical event before the current time.")
        value = self.read(event)
        month = value["months"][convention]
        if month is None:
            raise Unsupported("Historical lunar month needs independent review. No rule derived.")
        interval = value["interval"]
        rule = LunarRule(interval["paksha"], interval["paksha_day"], month["intercalation"],
                         convention, month["month"], repeated, "instant")
        spec = dict(kind="lunar", purpose=purpose, year=now.year, title=title,
                    time=reminder.strftime("%H:%M"), rule=asdict(rule), historical=self.evidence(event, value))
        return recurring.draft_spec(mode, offsets, spec, now, prefix=self.display(event, value))

    @staticmethod
    def evidence(event, value):
        return dict(version=VERSION, event_day=event.day.isoformat(), event_time=event.clock.isoformat(),
                    location=asdict(event.profile), instant=value["instant"].isoformat(),
                    profile=value["provenance"], interval=value["interval"], months=value["months"],
                    sunrise=value["sunrise"], sunrise_models=[d.isoformat() for d in value["dawns"]])

    def verify(self, spec):
        evidence = spec["historical"]
        event = HistoricalInput(date.fromisoformat(evidence["event_day"]), time.fromisoformat(evidence["event_time"]))
        try:
            return self.evidence(event, self.read(event)) == evidence
        except (Unsupported, Clarify):
            return False
