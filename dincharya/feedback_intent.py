"""Deterministic daily commands and short-lived Panchang follow-up intent."""
from datetime import datetime, timedelta
import re
from zoneinfo import ZoneInfo

from dincharya.lunar_intent import Clarify

IST = ZoneInfo("Asia/Kolkata")
RELATIVE = {"today":0,"tomorrow":1,"yesterday":-1}
MEDIA = {"voice":"voice messages","photo":"images","video":"videos","document":"documents",
         "video_note":"videos","animation":"videos","audio":"audio files"}
HELP = "Use /today, /tomorrow, /upcoming, /rules, /panchang or /status. Send a text appointment request for confirmation."
DAY_WORD = re.compile(r"\b(today|tomorrow|yesterday)(?:['’]s)?\b",re.I)
LUNAR_FOLLOW = re.compile(r"\b(?:remind|schedule)\b.*\b(?:this (?:tithi|year)|every year|when this occur)",re.I)


def panchang_question(text, now, remembered=None):
    from dincharya.historical_intent import DATE, NUMERIC_DATE
    q=text.strip()
    if q.startswith("/details "):
        q=q[9:]
    if q.startswith("/panchang"):
        parts=q.split(maxsplit=1)
        if parts[0]!="/panchang":
            return None
        q=parts[1] if len(parts)>1 else "today"
    local=now.astimezone(IST)
    if re.fullmatch(r"(?:what (?:is|was) )?(?:the )?(?:date )?(?:today|tomorrow|yesterday)(?:'s (?:date|tithi))?[?!.]?",q,re.I):
        word=DAY_WORD.search(q)[1].lower()
        return (local.date()+timedelta(days=RELATIVE[word])).isoformat()
    if re.fullmatch(r"(?:what is )?(?:the )?(?:tithi|date|panchang)(?: (?:now|today))?[?!.]?",q,re.I):
        return local.date().isoformat()
    if remembered and re.fullmatch(r"(?:and )?at (?:\d{1,2}:\d{2}|\d{1,2}\s*[ap]m)(?:\s*[ap]m)?[?.]?",q,re.I):
        return remembered["day"]+" "+re.sub(r"^and\s+","",q.rstrip("?."),flags=re.I)
    if DAY_WORD.search(q) and re.search(r"tithi|panchang|date",q,re.I):
        if DATE.search(q) or NUMERIC_DATE.search(q) or len(DAY_WORD.findall(q))!=1:
            raise Clarify("Give one Delhi date.")
        return DAY_WORD.sub(lambda m:(local.date()+timedelta(days=RELATIVE[m[1].lower()])).isoformat(),
                            re.sub(r"\bdate\b(?!\w)"," ",q,flags=re.I))
    if DATE.search(q) or NUMERIC_DATE.search(q):
        return q
    if re.search(r"tithi|panchang|तिथि|पंचांग",q,re.I):
        return q
    return None


def civil_relative(text,now):
    if not re.match(r"schedule\s",text,re.I):
        return text
    core, sep, tail=text.partition(";")
    local=now.astimezone(IST)
    match=re.fullmatch(r"(schedule\s+.+?)\s+in\s+(\d{1,3})\s+(minutes?|hours?)",core,re.I)
    if match:
        minutes=int(match[2])*(60 if match[3].lower().startswith("h") else 1)
        if not 1<=minutes<=7*1440:
            raise Clarify("Use a relative time from one minute to seven days.")
        at=local.replace(second=0,microsecond=0)+timedelta(minutes=minutes)
        core=f"{match[1]} on {at:%Y-%m-%d} at {at:%H:%M}"
    else:
        core=re.sub(r"\b(?:on )?(today|tomorrow) (?=at\s)",lambda m:
                    "on "+(local.date()+timedelta(days=RELATIVE[m[1].lower()])).isoformat()+" ",core,flags=re.I)
        core=re.sub(r"(\bat\s+)(\d{1,2})\s*([ap]m)\b",r"\g<1>\2:00 \3",core,flags=re.I)
    return core+sep+tail


def parse_followup(text, context, now):
    if not LUNAR_FOLLOW.search(text):
        return None
    if not context or not context.get("basis"):
        raise Clarify("Ask for one clear Delhi Panchang date or event time before scheduling this tithi.")
    raw,*options=[x.strip() for x in text.split(";")]
    pattern=r'(?:remind me(?: when this occurs?)?|schedule)\s*(?:"([^"\n]{1,60})"\s*)?(?:on this tithi\s+|this tithi\s+)?(this year|every year)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)[.?!]?'
    match=re.fullmatch(pattern,raw,re.I)
    if not match:
        raise Clarify('Use: Remind me "Anniversary" every year at 7 AM; Purnimanta; ordinary; review.')
    from dincharya.historical_intent import TIME, clock_value
    from dincharya.recurring_intent import notification
    at=match[3].strip().casefold()
    parsed_clock=TIME.fullmatch(at)
    if not parsed_clock:
        raise Clarify("Give HH:MM or a time with AM or PM.")
    clock=clock_value(parsed_clock,at)
    convention, repeated, requested, offsets="purnimanta","review",None,[0]
    seen=set()
    for option in options:
        option=option.casefold()
        if option in ("purnimanta","amanta"):
            field,convention="convention",option
        elif option in ("review","first","last"):
            field,repeated="repeated",option
        elif option in ("ordinary","adhika"):
            field,requested="intercalation",option
        else:
            field,offsets="notifications",notification(option)
        if field in seen:
            raise Clarify("Give each lunar option once.")
        seen.add(field)
    basis=context["basis"].get(convention)
    if basis is None or (requested and requested!=basis["intercalation"]):
        raise Clarify("The requested month is uncertain or its ordinary/Adhika distinction disagrees.")
    return dict(title=(match[1] or "Lunar anniversary").strip(),annual=match[2].lower()=="every year",
                clock=clock,offsets=offsets,rule={**basis,"repeated":repeated},
                year=now.astimezone(IST).year)
