"""Cycle 5 recurring rule review and rolling projection in the isolated service."""
from dataclasses import asdict
from datetime import date, datetime, time, timedelta
import re
from uuid import UUID, uuid4, uuid5

from dincharya.lunar_intent import Clarify, DIGITS, LUNAR, TITLE, parse_request
from dincharya.lunar_service import NAMESPACE, canonical
from prototypes.panchang.astronomy import DELHI, Unsupported

from prototypes.panchang.recurrence import LunarRule

REVIEW_WINDOW_DAYS = 400
POLICIES = ("none", "at_start", "before_start", "before_and_at_start")
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
DAY_ALIASES = ("सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार")
CIVIL = re.compile(r"^(?:schedule|मुझे|mujhe)\s+", re.I)
NOTIFICATION_EDIT = re.compile(
    r"(?:remind me|याद दिलाओ|yaad dilao)\s+(.+?)\s+(?:before|पहले|pehle)\s+(?:my |मेरी |meri )?(.+?)[.!।]?",
    re.I,
)
OFFSET = re.compile(r"([0-9]{1,5})\s*(minutes?|mins?|hours?|hrs?|days?|मिनट|घंटे|दिन|ghante|din)")
UNIT = {"m": 1, "h": 60, "d": 1440, "म": 1, "घ": 60, "द": 1440, "g": 60}


def notification(text):
    """Explicit policy syntax shared by drafts and policy edits."""
    text = text.translate(DIGITS).strip().casefold()
    text = re.sub(r"\b(?:one|ek|एक)\s+", "1 ", text)
    if text in {"none", "no reminder", "don't remind me", "do not remind me", "याद मत दिलाओ", "yaad mat dilao"}:
        return []
    if text in {"at_start", "at start", "शुरू होते ही", "shuru hote hi"}:
        return [0]
    parts = re.split(r"\s*(?:,|\band\b|और|\baur\b)\s*", text)
    offsets = []
    for part in parts:
        if part in {"at start", "at_start", "शुरू होते ही", "shuru hote hi"}:
            offsets.append(0)
            continue
        match = OFFSET.fullmatch(re.sub(r"\s+(?:before|पहले|pehle)$", "", part))
        if not match:
            raise Clarify("Specify reminder offsets, at start, or none.")
        offset = int(match[1]) * UNIT[match[2][0]]
        if not 1 <= offset <= 10080:
            raise Clarify("Advance reminders must be 1 minute to 7 days before the activity.")
        offsets.append(offset)
    if len(offsets) != len(set(offsets)) or len(offsets) > 9:
        raise Clarify("Use at most nine distinct reminders.")
    return sorted(offsets)


def policy_name(offsets):
    return POLICIES[0 if not offsets else 1 if offsets == [0] else 3 if 0 in offsets else 2]


def clock_text(raw):
    match = re.fullmatch(r"([0-9]{1,2}):([0-9]{2})\s*(am|pm)?", raw.strip().casefold())
    if not match:
        raise Clarify("Give a time such as 06:30 or 6:30 AM.")
    hour, minute = int(match[1]), int(match[2])
    if match[3]:
        if not 1 <= hour <= 12:
            raise Clarify("Give a valid AM/PM time.")
        hour = hour % 12 + (12 if match[3] == "pm" else 0)
    try:
        return time(hour, minute).strftime("%H:%M")
    except ValueError:
        raise Clarify("Give a valid time.") from None


def parse_recurring(text, today, now=None):
    if not isinstance(text, str) or len(text) > 1200:
        raise Clarify("Send a short recurring activity.")
    # A semicolon explicitly separates the approval and notification clauses.
    chunks = [chunk.strip() for chunk in text.split(";")]
    raw = chunks[0].translate(DIGITS)
    mode, offsets = "automatic", []
    seen = set()
    for chunk in chunks[1:]:
        candidate = chunk.casefold()
        if candidate in {"automatic", "manual", "स्वचालित", "मैनुअल", "approve future years automatically"}:
            field = "mode"
            mode = "manual" if candidate in {"manual", "मैनुअल"} else "automatic"
        else:
            field = "notifications"
            offsets = notification(re.sub(r"^(?:notify|remind me|याद दिलाओ|yaad dilao)\s+", "", candidate))
        if field in seen:
            raise Clarify("Provide one approval mode and one notification clause.")
        seen.add(field)
    if LUNAR.search(TITLE.sub("", raw)):
        if "notifications" not in seen and re.search(r"remind me|याद दिलाओ|yaad dilao", raw, re.I):
            offsets = [0]
        raw = re.sub(r"(?i)(?<!\d)([0-9]{1,2}(?::[0-9]{2})?\s*(?:AM|PM))(?!\w)",
                     lambda match: clock_text(re.sub(r"^(\d+)\s*([ap]m)$", r"\1:00 \2", match[1], flags=re.I)), raw)
        intent = parse_request(raw)
        if "annual_year" not in intent:
            raise Clarify("An annual lunar rule needs a start year and a named lunar month.")
        if not today.year <= intent["annual_year"] <= min(2099, today.year + 5):
            raise Clarify("Choose a start year within the next five years.")
        if intent["rule"]["intercalation"] == "both":
            raise Clarify("Choose ordinary or Adhika.")
        rule = LunarRule(**intent["rule"])
        return mode, offsets, dict(kind="lunar", purpose=intent["purpose"], rule=asdict(rule),
                                  year=intent["annual_year"], title=intent["title"], time=intent["time"])

    if mode != "automatic":
        raise Clarify("Manual review is available for lunar annual rules.")
    match = re.fullmatch(
        r"(?:schedule|मुझे|mujhe)\s+(.+?)\s+"
        r"(every day|daily|रोज़|रोज|roz|हर दिन|har din|"
        r"(?:(?:each|every|हर|har)\s+)?(?:" + "|".join(DAYS + DAY_ALIASES) + r")|"
        r"(?:every year on|annually on|हर साल|har saal)\s+[0-9]{2}-[0-9]{2}|"
        r"(?:on|दिनांक|tareekh)\s+[0-9]{4}-[0-9]{2}-[0-9]{2})"
        r"(?:\s+(?:at|को|ko))?\s+([0-9]{1,2}:[0-9]{2}\s*(?:am|pm)?)(?:\s+(?:बजे|baje|IST))?"
        r"(?:,\s*but\s+don\x27t remind me\.?)?", raw, re.I)
    if not match:
        raise Clarify("Use a daily or weekly rule, every year on MM-DD, on YYYY-MM-DD, or an explicit annual lunar rule.")
    if re.search(r"don't remind me", raw, re.I) and offsets:
        raise Clarify("The request gives conflicting reminder preferences.")
    name, day, at = match.groups()
    title = name.strip('"“” ')
    if not title or len(title) > 80 or any(not c.isprintable() for c in title):
        raise Clarify("Use a short activity title.")
    day = re.sub(r"^(?:each|every|हर|har)\s+", "", day.casefold(), count=1) if not re.search(r"\d", day) else day
    weekday = (DAYS.index(day)+1 if day in DAYS else DAY_ALIASES.index(day)+1 if day in DAY_ALIASES else None)
    start = today
    if now is not None and clock_text(at) <= now.strftime("%H:%M"):
        start += timedelta(days=1)
    if weekday:
        start += timedelta(days=(weekday-start.isoweekday()) % 7)
    civil = dict(calendar_system="gregorian", frequency="weekly" if weekday else "daily",
                 interval_count=1, start_date=start.isoformat())
    if weekday:
        civil["weekdays"] = [weekday]
    elif day.split()[-1].count("-") == 2:
        try:
            eligible = date.fromisoformat(day.split()[-1])
        except ValueError:
            raise Clarify("Give a valid Gregorian date.") from None
        if eligible < start:
            raise Clarify("Give a future appointment time.")
        civil.update(frequency="once", start_date=eligible.isoformat())
    elif re.search(r"\d", day):
        month, month_day = map(int, day.split()[-1].split("-"))
        try:
            date(2000, month, month_day)
        except ValueError:
            raise Clarify("Give a valid Gregorian month and day.") from None
        for year in range(start.year, start.year + 9):
            try:
                eligible = date(year, month, month_day)
            except ValueError:  # February 29 in a common year.
                continue
            if eligible >= start:
                break
        civil.update(frequency="yearly", start_date=eligible.isoformat(), months=[month], month_days=[month_day])
    desired = dict(title=title, timezone="Asia/Kolkata", start_time=clock_text(at), recurrence_rule=civil)
    return mode, offsets, dict(kind="gregorian", desired=desired)


def call(adapter, function, params):
    # Only fixed names are passed by trusted callers, never by chat input.
    placeholders = ",".join(["%s"] * len(params))
    return adapter._call(f"SELECT lunar_api.{function}({placeholders})", params)


class Recurring:
    def __init__(self, development):
        self.dev = development
        self.owner = development.owner

    def draft(self, text):
        now = datetime.fromtimestamp(self.dev.clock(), DELHI)
        edit = NOTIFICATION_EDIT.fullmatch(text.translate(DIGITS).strip()) if isinstance(text, str) else None
        if edit:
            offsets, title = edit.groups()
            rows = [row for row in self.controls()["controls"]
                    if row["state"] != "cancelled" and row["title"].casefold() == title.strip('"“” ').casefold()]
            if len(rows) != 1:
                raise Clarify("Give the exact title of one managed rule, or use /recurring_change with its ID.")
            return self.change_preview(rows, dict(control=rows[0]["id"], change="notifications", policy=offsets))
        mode, offsets, spec = parse_recurring(text, now.date(), now)
        eligible = "No safe occurrence in the rolling window."
        warnings = []
        if spec["kind"] == "lunar":
            self.bind_series(spec)

            for year in self.years(spec["year"], now.date()):
                try:
                    plan = self.plan(spec, year)
                    if plan["row"]["selected_date"] <= (now.date() + timedelta(days=REVIEW_WINDOW_DAYS)).isoformat():
                        eligible = f'{plan["row"]["selected_date"]} at {spec["time"]}'
                        break
                except Unsupported as error:
                    if str(error) != "appointment_is_in_the_past":
                        warnings.append(f"{year}: {error}")
            label = f'{spec["title"]} · annual {spec["rule"]["convention"]} {spec["rule"]["month"]}, ' \
                    f'{spec["rule"]["paksha"]} tithi {spec["rule"]["tithi"]}, {spec["rule"]["intercalation"]}, ' \
                    f'repeat {spec["rule"]["repeated"]}'
        else:
            desired = spec["desired"]
            rule = desired["recurrence_rule"]
            label = f'{desired["title"]} · Gregorian {rule["frequency"]}'
            if rule["frequency"] == "weekly":
                label += f' {DAYS[rule["weekdays"][0]-1].title()}'
            if rule["frequency"] == "yearly":
                label += f' on {rule["months"][0]:02d}-{rule["month_days"][0]:02d}'
            eligible = f'{desired["recurrence_rule"]["start_date"]} at {desired["start_time"]}'
        details = f"{label}\n{mode} · {policy_name(offsets)} · offsets {offsets} minutes\nAsia/Kolkata · {eligible}"
        if warnings:
            details += "\nWithheld: " + "; ".join(warnings)
        # Gregorian intent changes require a separate approved edit, not an
        # accidental second rule from a new preview with different offsets.
        name = spec if spec["kind"] == "lunar" else {
            **spec["desired"], "recurrence_rule": {k: v for k, v in spec["desired"]["recurrence_rule"].items()
                                                   if k != "start_date" or rule["frequency"] == "once"}}
        key = uuid5(NAMESPACE, "recurring/" + canonical(name))
        return self.dev._issue(dict(recurring=(key, mode, offsets, spec)), details, "rule_preview")

    def bind_series(self, spec):
        spec["rule"]["profile"] = self.dev.profile
        key = dict(title=spec["title"], time=spec["time"], rule={
            k: v for k, v in spec["rule"].items() if k not in {"profile", "repeated"}})
        spec["series"] = str(uuid5(NAMESPACE, "development-annual/" + canonical(key)))

    @staticmethod
    def years(first, today):
        last = min(2099, (today + timedelta(days=REVIEW_WINDOW_DAYS)).year)
        return range(max(first, today.year), last + 1)

    def plan(self, spec, year):
        rule = {key: value for key, value in spec["rule"].items() if key != "profile"}
        return self.dev._selection(dict(rule=rule, title=spec["title"], time=spec["time"],
                                        annual_year=spec["year"], start=f"{year}-01-01",
                                        end=f"{year+1}-01-01"))

    def approve(self, args, expires):
        key, mode, offsets, spec = args
        result = call(self.owner, "approve_recurring",
                      (key, mode, offsets, self.owner._json(spec), datetime.fromtimestamp(expires, DELHI)))
        return dict(status="approved", reply=f'Rule approved. ID {result["id"]}.', control=result["id"])

    def controls(self):
        return call(self.owner, "recurring_controls", ())

    def reserve_alert(self):
        alert = call(self.owner, "reserve_recurring_alert", ())
        if not alert:
            return dict(status="no_alert")
        return dict(status="alert", reply=f'{alert["title"]} · {alert["year"]} withheld ({alert["reason"]}). '
                    "Review with /recurring_rules.")

    def adopt_preview(self, identifier, mode):
        try:
            series = UUID(identifier)
        except (ValueError, TypeError):
            raise Clarify("Use a series ID from /lunar_rules.") from None
        if mode not in {"manual", "automatic"}:
            raise Clarify("Choose manual or automatic.")
        row = self.owner.inspect_annual_rule(series)
        annual, saved = row["annual"], row["series"]
        if not saved["enabled"]:
            raise Clarify("The annual rule is cancelled.")
        if any(item["series_id"] == str(series) for item in self.controls()["controls"]):
            raise Clarify("Use /recurring_change for this managed rule.")
        spec = dict(kind="lunar", series=str(series), purpose=saved["purpose"], rule=saved["rule"],
                    title=annual["title"], time=annual["appointment_time"][:5], year=annual["start_year"])
        rule = saved["rule"]
        details = (f'{spec["title"]} · annual {rule["convention"]} {rule["month"]}, {rule["paksha"]} '
                   f'tithi {rule["tithi"]}, {rule["intercalation"]}, repeat {rule["repeated"]}\n'
                   f'{mode} · at_start · offset 0 minutes\nAsia/Kolkata · {spec["time"]}\n'
                   "Existing appointments retain history. New lunar dates require the sunrise checks.")
        return self.dev._issue(dict(recurring=(uuid5(series, "cycle5-adoption"), mode, [0], spec)),
                               details, "rule_preview")

    def change_preview(self, rows, args):
        try:
            key = UUID(args["control"])
            row = next(item for item in rows if item["id"] == str(key))
        except (ValueError, TypeError, StopIteration):
            raise Clarify("Select a rule from /recurring_rules.") from None
        action = args["change"]
        if action not in {"pause", "resume", "cancel", "notifications", "replace", "automatic", "manual"}:
            raise Clarify("Use pause, resume, cancel, notifications, replace, automatic, or manual.")
        if action in {"automatic", "manual"} and not row["series_id"]:
            raise Clarify("Use approval-mode changes on annual lunar rules.")
        offsets = notification(args["policy"]) if action == "notifications" else []
        spec = None
        if action == "replace":
            now = datetime.fromtimestamp(self.dev.clock(), DELHI)
            _, _, spec = parse_recurring(args["policy"], now.date(), now)
            if spec["kind"] == "lunar":
                self.bind_series(spec)
                spec["series"] = str(uuid4())
        fingerprint = call(self.owner, "recurring_fingerprint", (key,))
        data = (key, row["revision"], uuid4(), action, offsets, fingerprint, self.owner._json(spec))
        detail = (f" · {policy_name(offsets)} · offsets {offsets}" if action == "notifications" else
                  f" · replacement {args['policy']}" if action == "replace" else "")
        return self.dev._issue(dict(recurring_change=data),
                               f'{action} rule {key} at revision {row["revision"]}'
                               + detail,
                               "rule_preview")

    def change(self, args, expires):
        result = call(self.owner, "reviewed_recurring_change", (*args, datetime.fromtimestamp(expires, DELHI)))
        return dict(status="approved", reply=f'Rule updated. State {result["state"]}, revision {result["revision"]}.')

    def project(self):
        today = datetime.fromtimestamp(self.dev.clock(), DELHI).date()
        current = self.controls()
        seen = {(x["control"], x["target_year"]) for x in current["withheld"]}
        alerts = []
        for control in current["controls"]:
            if control["state"] != "active" or control["mode"] != "automatic" or not control["series_id"]:
                continue
            series = UUID(control["series_id"])
            snapshot = self.owner.inspect_annual_rule(series)
            if not snapshot["series"]["enabled"]:
                continue
            annual = snapshot["annual"]
            rule = snapshot["series"]["rule"]
            spec = dict(rule=rule, title=annual["title"], year=annual["start_year"],
                        time=annual["appointment_time"][:5])
            key = UUID(control["id"])
            version = control["revision"]
            for year in self.years(spec["year"], today):
                if year in control["closed_years"] or (str(key), year) in seen:
                    continue
                try:
                    if rule["profile"] != self.dev.profile:
                        raise Unsupported("reference_profile_changed")
                    plan = self.plan(spec, year)
                    if date.fromisoformat(plan["row"]["selected_date"]) > today + timedelta(days=REVIEW_WINDOW_DAYS):
                        continue
                    occurrence = self.dev._calculation(plan, series, snapshot["series"]["revision"], True)
                    row = self.owner.inspect_occurrence(occurrence)["occurrence"]
                    if row["cancelled"]:
                        continue
                    label = f'{version}/{row["observation"]}'
                    result = call(self.owner, "project_recurring",
                                  (key, version, occurrence, uuid5(occurrence, "auto/proposal/" + label),
                                   uuid5(occurrence, "auto/decision/" + label), row["observation"]))
                    if result["status"] == "conflict":
                        raise Unsupported("schedule_conflict")
                except Unsupported as error:
                    if str(error) == "appointment_is_in_the_past":
                        continue
                    call(self.owner, "recurring_withhold", (key, version, year, str(error)[:100]))
                    alerts.append(f"{key} · {year} · {error}")
        return dict(status="projected", alerts=alerts, reply="\n".join(alerts) or "Projection check complete.")
