"""Personal lunar projection candidates gated by pinned Delhi civil-day evidence."""
from datetime import date
import json

from prototypes.panchang.astronomy import Unsupported
from prototypes.panchang.guarded import REFERENCE_PATH
from prototypes.panchang.recurrence import LunarRule, logical_key


def rule_key(rule):
    return f"{rule.month}-{rule.convention}-{rule.paksha}-{rule.tithi}"


def candidate(calendar, rule, year):
    rule=LunarRule(**rule)
    if rule.intercalation not in ("ordinary","adhika") or rule.month is None or not 1901<=year<=2099:
        return None
    rows=json.loads(REFERENCE_PATH.with_name("historical-references.json").read_bytes())["future_comparisons"]
    matches=[r for r in rows if r["year"]==year and r["rule"]==rule_key(rule)
             and r.get("intercalation","ordinary")==rule.intercalation]
    if len(matches)!=1 or not matches[0]["selected"]:
        return None
    try:
        verified=calendar(rule,date(year,1,1),date(year+1,1,1))
    except Unsupported:
        return None
    selection=matches[0].get("selection","single")
    dawns=verified["sunrise_dates"]
    if verified["selected_date"]!=matches[0]["selected"]:
        return None
    if selection=="single":
        if len(dawns)!=1:
            return None
    elif len(dawns)!=2 or selection not in ("first","last") or rule.repeated!=selection:
        return None
    return dict(day=verified["selected_date"],year=year,rule=rule_key(rule),
                month_kind=rule.intercalation,identity=logical_key(verified["identity"]))
