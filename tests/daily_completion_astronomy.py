"""Changed-path pinned astronomy test entry point. Run in the astronomy-only child."""
from datetime import date, time
import json
import sys
import sysconfig

sys.path[:0]=[sys.argv[1],"/repo"]
sys.path.extend([sysconfig.get_path("purelib"),sysconfig.get_path("platlib")])

from dincharya.historical_panchang import HistoricalInput, HistoricalPanchang
from dincharya.personal_lunar import candidate
from prototypes.panchang.astronomy import Astronomy, Unsupported
from prototypes.panchang.guarded import GuardedCalendar, REFERENCE_PATH, guarded_occurrence
from prototypes.panchang.recurrence import LunarRule, RecurrenceResearch, logical_key

kernel=sys.argv[2]
calendar=GuardedCalendar(kernel)
# An invented event instant on a public reference day, with a separate
# occurrence convention and independent next-year date evidence.
event=HistoricalInput(date(2025,11,14),time(10))
reading=HistoricalPanchang(calendar).read(event)
actual=reading["months"]["purnimanta"]
assert (reading["interval"]["ordinal"],actual["month"],actual["intercalation"])==(25,"margashirsha","ordinary")
rule=dict(paksha="krishna",tithi=10,intercalation="ordinary",month=actual["month"],
          convention="purnimanta",repeated="review",birth_basis="instant")
refs=json.loads(REFERENCE_PATH.with_name("personal-annual-references.json").read_bytes())["rows"]
results=[candidate(calendar,rule,row["year"]) for row in refs]
assert [r["day"] for r in results]==[r["selected"] for r in refs]
assert len({r["identity"] for r in results})==len(refs)==3
assert candidate(calendar,rule,2029) is None
assert candidate(calendar,rule | {"intercalation":"adhika"},2027) is None
print("PASS event instant; ordinary Purnimanta 2026–2028; distinct year identities; mismatch withheld")

with Astronomy(kernel) as astronomy:
    adhika=LunarRule("shukla",10,"adhika","purnimanta","shravana","review","instant")
    assert guarded_occurrence(astronomy,adhika,date(2023,7,25),date(2023,8,1))["selected_date"]=="2023-07-28"
    assert RecurrenceResearch(astronomy).annual(adhika,2026)["occurrences"]==[]
    known = json.loads(REFERENCE_PATH.read_bytes())["selection_cases"][0]
    def repeat(policy):
        return LunarRule("shukla",12,"ordinary","purnimanta","chaitra",policy,"instant")
    search = tuple(date.fromisoformat(d) for d in known["window"])
    outcomes=[guarded_occurrence(astronomy,repeat(p),*search) for p in ("first","last")]
    assert [r["selected_date"] for r in outcomes]==[known["first"],known["last"]]
    assert logical_key(outcomes[0]["identity"])==logical_key(outcomes[1]["identity"])
    try:
        guarded_occurrence(astronomy,repeat("review"),*search)
    except Unsupported as error:
        assert str(error)=="repeated_requires_policy"
    else:
        raise AssertionError("repeated sunrise allowed without policy")
    skipped=LunarRule("krishna",11,"ordinary","purnimanta","shravana","first","instant")
    try:
        guarded_occurrence(astronomy,skipped,date(2027,7,27),date(2027,8,2))
    except Unsupported as error:
        assert str(error)=="skipped_at_sunrise"
    else:
        raise AssertionError("skipped sunrise projected")
print("PASS Adhika distinction; repeated first/last and review fence; skipped date withheld")
