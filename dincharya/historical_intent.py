"""Bounded Delhi date and anniversary request parsing; no ephemeris dependency."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
import re

from dincharya.lunar_intent import Clarify, DIGITS
from dincharya.recurring_intent import notification
from zoneinfo import ZoneInfo

DELHI=ZoneInfo("Asia/Kolkata")
UTC=timezone.utc

DATE_FORMS = {
    "january": "jan जनवरी", "february": "feb फरवरी फ़रवरी", "march": "mar मार्च",
    "april": "apr अप्रैल", "may": "मई", "june": "jun जून", "july": "jul जुलाई",
    "august": "aug अगस्त", "september": "sep sept सितंबर सितम्बर",
    "october": "oct अक्टूबर", "november": "nov नवंबर नवम्बर", "december": "dec दिसंबर दिसम्बर",
}
MONTH_NUMBER = {alias: month for month, (name, aliases) in enumerate(DATE_FORMS.items(), 1)
                for alias in (name, *aliases.split())}
NUMERIC_DATE = re.compile(r"(?<![\w/-])([0-9]{1,2})([/.-])([0-9]{1,2})\2([0-9]{4})(?![\w/-])")
DATE = re.compile(r"(?<![\w-])(?:([0-9]{4}-[0-9]{2}-[0-9]{2})|([0-9]{1,2})(?:st|nd|rd|th)?\s+("
                  + "|".join(MONTH_NUMBER) + r")\s+([0-9]{4}))(?![\w-])", re.I)
TIME = re.compile(r"(?<![\w:])([0-9]{1,2})(?::([0-9]{2})(?::([0-9]{2}))?)?"
                  r"\s*(am|pm|सुबह|शाम|subah|shaam|बजे|baje)?(?![\w:])", re.I)
DELHI_TEXT = re.compile(r"(?<!\w)(?:new delhi|nai dilli|delhi|dilli|नई दिल्ली|दिल्ली)(?!\w)", re.I)
QUERY = re.compile(r"\b(?:what (?:was|were|is)|panchang lookup|kaunsi tithi|kya tithi|kya thi|kya tha)\b|क्या|कौन सी", re.I)
EVENT = re.compile(r"\b(?:born|married|birth|wedding|marriage|significant event|janam|janm|shaadi)\b|जन्म|शादी|विवाह", re.I)
ANNUAL = re.compile(r"\b(?:annual(?:ly)?|yearly|every year|har saal|saalana)\b|हर साल|वार्षिक|सालाना", re.I)
NAMES = ("Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami",
         "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi")
BASIS_WORDS = frozenset(("what was were is on at in for of the my tithi lunar details detail panchang lookup "
                        "ka ki ke ko thi tha hui hua mera meri mujhe main mein dilli kaunsi kya tareekh ist "
                        "क्या थी था है कौन सी को की के में पर तिथि पंचांग बताओ बताएं विवरण मेरा मेरी आईएसटी").split())
EVENT_WORDS = frozenset(("i was born married birth wedding marriage significant event my on at in date "
                        "janam janm shaadi mera meri hua hui ko mein baje ist साल तारीख मेरा मेरी मुझे जन्म "
                        "हुआ हुई शादी विवाह को में पर बजे आईएसटी").split())
SCHEDULE = re.compile(r"^(?:remind me|schedule|set|yaad dilao|याद दिलाओ|याद दिलाना|रिमाइंडर)(?!\w)", re.I)


@dataclass(frozen=True)
class DelhiProfile:
    name: str = "New Delhi"
    latitude: float = 28.6139
    longitude: float = 77.2090
    timezone: str = "Asia/Kolkata"


PROFILE = DelhiProfile()


@dataclass(frozen=True)
class HistoricalInput:
    day: date
    clock: time | None
    profile: DelhiProfile = PROFILE

    def instant(self):
        if self.clock is None:
            raise Clarify("Give the event's exact local time.")
        return local_instant(self.day, self.clock)


def local_candidates(naive):
    # Distinct UTC candidates identify a historical fold. A gap round-trips
    # to a different wall time, even if zoneinfo supplies a nominal offset.
    instants = set()
    for fold in (0, 1):
        local = naive.replace(tzinfo=DELHI, fold=fold)
        utc = local.astimezone(UTC)
        if utc.astimezone(DELHI).replace(tzinfo=None) == naive:
            instants.add(utc)
    return sorted(instants)


def local_instant(day, clock):
    instants = local_candidates(datetime.combine(day, clock))
    if len(instants) != 1:
        raise Clarify("That Delhi local time is ambiguous or did not occur. Give an unambiguous local time.")
    if not 1900<=instants[0].year<=2100:
        raise Clarify("The pinned ephemeris covers UTC years 1900 through 2100.")
    return instants[0]


def civil_start(day):
    midnight = datetime.combine(day, time.min)
    for minutes in range(24 * 60):
        instants = local_candidates(midnight + timedelta(minutes=minutes))
        if instants:
            return instants[0]
    raise Clarify("The requested local civil date did not occur")


def clock_value(match, text):
    hour, minute, second = (int(x or 0) for x in match.groups()[:3])
    suffix = match[4]
    if not match[2] and not suffix:
        raise Clarify("Give HH:MM or a time with AM or PM.")
    lower, upper = ("am", "सुबह", "subah"), ("pm", "शाम", "shaam")
    prefix = re.search(r"(?:सुबह|शाम|subah|shaam)\s*$", text[:match.start()])
    if prefix:
        qualifier = prefix[0].strip()
        if suffix in lower + upper and (suffix in lower) != (qualifier in lower):
            raise Clarify("The clock gives conflicting morning and evening markers.")
        suffix = qualifier
    if suffix in lower + upper:
        if not 1 <= hour <= 12:
            raise Clarify("Use a valid 12-hour clock time.")
        hour = hour % 12 + (12 if suffix in upper else 0)
    try:
        return time(hour, minute, second)
    except ValueError:
        raise Clarify("Give a valid local clock time.") from None


def extract(text, *, event=False):
    if not isinstance(text, str) or not 1 <= len(text) <= 1000 or "\n" in text:
        raise Clarify("Send one short request with one date.")
    text = text.translate(DIGITS).casefold().replace("।", ".")
    dates = [*DATE.finditer(text), *NUMERIC_DATE.finditer(text)]
    if len(dates) != 1:
        raise Clarify("Use a single date such as 6 December 2023 or 2023-12-06.")
    match = dates[0]
    try:
        if match.re is NUMERIC_DATE:
            day = date(int(match[4]),int(match[3]),int(match[1]))
        else:
            day = date.fromisoformat(match[1]) if match[1] else date(int(match[4]), MONTH_NUMBER[match[3]], int(match[2]))
    except ValueError:
        raise Clarify("That Gregorian date does not exist.") from None
    suffix = text[match.end():]
    rest = text[:match.start()] + " " + suffix
    locations = list(DELHI_TEXT.finditer(rest))
    if len(locations) > 1 or (event and not locations):
        raise Clarify("Give one verified location, Delhi or New Delhi.")
    rest = DELHI_TEXT.sub(" ", rest)
    times = list(TIME.finditer(rest))
    if len(times) > 1:
        raise Clarify("Give one historical event time.")
    clock = clock_value(times[0], rest) if times else None
    if event and clock is None:
        raise Clarify("Give the event's exact local time.")
    if times:
        rest = rest[:times[0].start()] + " " + rest[times[0].end():]
    rest = re.sub(r"(?:सुबह|शाम|subah|shaam)(?=\s|[,.?!—–-]|$)", " ", rest)
    rest = re.sub(r"[,\.?!—–-]", " ", rest)
    if set(rest.split()) - (EVENT_WORDS if event else BASIS_WORDS):
        raise Clarify("Use a supported date and Delhi location. Other locations and extra time qualifiers need clarification.")
    if not 1900 <= day.year <= 2100:
        raise Clarify("The pinned ephemeris covers UTC years 1900 through 2100.")
    return HistoricalInput(day, clock)


def historical_route(text):
    if not isinstance(text, str) or len(text) > 1000:
        return None
    if EVENT.search(text) and ANNUAL.search(text):
        return "draft_historical_anniversary"
    if QUERY.search(text) and ("tithi" in text.casefold() or "panchang" in text.casefold()
                              or "lunar details" in text.casefold() or "तिथि" in text or "पंचांग" in text):
        return "historical_panchang"
    return None


def historical_text(text):
    if not isinstance(text, str):
        raise Clarify("Send one Panchang question.")
    return extract(text)


def anniversary_text(text):
    if not isinstance(text, str) or len(text) > 1000:
        raise Clarify("Give one historical event and a separate future reminder time.")
    base, *clauses = [part.strip() for part in text.split(";")]
    sections = re.split(r"(?<=[.!?।])\s+", base, maxsplit=1)
    if len(sections) != 2 or not EVENT.search(sections[0]) or not ANNUAL.search(sections[1]) or not SCHEDULE.match(sections[1]):
        raise Clarify("Describe the historical event in one sentence, then request an annual reminder in the next.")
    source, request = sections
    request = request.translate(DIGITS).casefold()
    appointments = list(TIME.finditer(request))
    if len(appointments) != 1:
        raise Clarify("Give a separate future reminder time, for example ‘remind me every year at 7 AM’.")
    reminder = clock_value(appointments[0], request)
    if reminder.second:
        raise Clarify("Use minute precision for the future reminder time.")
    remainder = request[:appointments[0].start()] + " " + request[appointments[0].end():]
    words = frozenset(("remind me schedule set my a on at in the lunar hindu calendar hindu-calendar birthday "
                       "anniversary reminder every year annual annually yearly har saal saalana yaad dilao janam "
                       "shaadi salgirah baje ko subah shaam ist याद दिलाओ दिलाना रिमाइंडर हर साल सालाना वार्षिक "
                       "जन्मदिन सालगिरह विवाह तिथि पंचांग हिन्दू हिंदू को बजे सुबह शाम").split())
    if set(re.sub(r"[,\.?!—–।]", " ", remainder).split()) - words:
        raise Clarify("Use explicit annual wording and put the calendar convention or reminder offsets after a semicolon.")
    mode, convention, repeated, offsets = "automatic", "purnimanta", "review", [0]
    seen = set()
    for raw in clauses:
        value = raw.casefold().rstrip(".")
        if value in {"automatic", "manual"}:
            key, mode = "mode", value
        elif value in {"amanta", "purnimanta", "अमांत", "पूर्णिमांत"}:
            key = "convention"
            convention = "amanta" if value in {"amanta", "अमांत"} else "purnimanta"
        elif value in {"first", "last", "review"}:
            key, repeated = "repeat", value
        else:
            key, offsets = "notifications", notification(value)
        if key in seen:
            raise Clarify("Give each policy option once.")
        seen.add(key)
    event = extract(source, event=True)
    title, purpose = ("Lunar birthday", "birthday") if re.search(r"born|birth|janm|janam|जन्म", source, re.I) else (
        ("Lunar wedding anniversary", "wedding_anniversary") if re.search(r"married|marriage|wedding|shaadi|विवाह|शादी", source, re.I)
        else ("Lunar anniversary", "monthly"))
    return event, reminder, mode, convention, repeated, offsets, title, purpose


def label(ordinal):
    paksha = "Shukla" if ordinal <= 15 else "Krishna"
    name = NAMES[(ordinal-1) % 15] if ordinal not in (15, 30) else ("Purnima" if ordinal == 15 else "Amavasya")
    return f"{paksha} {name}"


def local_text(value):
    return value.astimezone(DELHI).strftime("%Y-%m-%d %H:%M %Z")
