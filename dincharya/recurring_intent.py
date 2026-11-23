"""Side-effect-free proposal parser shared by development and beta previews."""
from dataclasses import asdict
from datetime import date, time, timedelta
import re

from dincharya.lunar_intent import Clarify, DIGITS, LUNAR, TITLE, parse_request

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


def parse_recurring(text, today, now=None, *, civil_only=False):
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
    if civil_only and (LUNAR.search(raw) or re.search(
            r"(?:festival|ekadashi|purnima|amavasya|diwali|एकादशी|पूर्णिमा|अमावस्या|दिवाली)", raw, re.I)):
        raise Clarify("Lunar and festival scheduling is withheld in the personal beta.")
    if LUNAR.search(TITLE.sub("", raw)):
        from prototypes.panchang.recurrence import LunarRule

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
    if civil_only and re.search(r"(?<!\w)(?:every|daily|weekly|yearly|annually|har|हर|रोज|roz)(?!\w)|[0-9]{2}:[0-9]{2}", name, re.I):
        raise Clarify("Give one activity, one recurrence and one start time.")
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
