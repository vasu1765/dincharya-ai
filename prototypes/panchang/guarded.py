"""Cycle 1 Delhi date selection for the isolated development approval path."""
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path

from .astronomy import Astronomy, DELHI, Unsupported
from .recurrence import DATE_GUARD_SECONDS, RecurrenceResearch
from .reference_policy import PUBLISHER_TOLERANCE_SECONDS

MODELS = ("upper_limb_50", "pac_47_hypothesis")
POLICY = "drik-delhi-pac-corroboration-v1"
REFERENCE_PATH = Path(__file__).with_name("calendar-references.json")
EXTRA_DELHI_ORDINALS = (("2026-06-30", 16),)
# Public May 1 comparison recorded in the Cycle 1 report. Same geocentric
# endpoint, despite PAC using its central station to group the day on paper.
EXTRA_ENDPOINTS = (
    (23, "2024-05-01T05:45:00+05:30"),
    (23, "2024-05-01T05:47:00+05:30"),
)


def delhi_observations():
    """Use local direct observations. PAC central-station labels are a different profile."""
    refs = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    delhi = (row for row in refs["calendar_days"]
             if row.get("source", "").startswith("drik") or "pdf_page_1based" in row)
    return tuple((row["day"], row["ordinal"]) for row in delhi) + EXTRA_DELHI_ORDINALS


def fingerprints(directory=REFERENCE_PATH.parent):
    """Version the public inputs used by the guarded development profile."""
    return {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
            for name in ("calendar-references.json", "research-references.json",
                         "references.json", "feasibility-results.json",
                         "validation-results.json", "recurrence-results.json")}


def publisher_endpoints():
    endpoints = []
    for name, key in (("references.json", "transitions"),
                      ("research-references.json", "additional_transitions"),
                      ("calendar-references.json", "timing_diagnostics")):
        data = json.loads(REFERENCE_PATH.with_name(name).read_text(encoding="utf-8"))
        endpoints.extend((row["ordinal"], row["at"]) for row in data[key]
                         if row["source"] in {"drik_ekadashi", "drik2026", "pac2023"})
    return tuple(endpoints) + EXTRA_ENDPOINTS


def edge_window(edge, ordinal, endpoints):
    # Only use the matching geocentric tithi boundary. The civil day is checked
    # in IST and the ordinal repeats approximately monthly.
    matches = [datetime.fromisoformat(stamp) for n, stamp in endpoints if n == ordinal]
    matches = [at for at in matches if abs(at - edge) < timedelta(days=1)]
    return (min([edge - timedelta(seconds=0.05)]
                + [at - timedelta(seconds=30) for at in matches]),
            max([edge] + [at + timedelta(minutes=1) for at in matches]))


def guarded_occurrence(astronomy, rule, start, end, *, references=None, endpoints=None):
    """Return exactly one agreed choice, or withhold with a stable reason."""
    previews = [RecurrenceResearch(astronomy, model).preview(rule, start, end)
                for model in MODELS]
    left, right = [preview["occurrences"] for preview in previews]
    if len(left) > 1 or len(right) > 1:
        raise Unsupported("multiple_occurrences_require_narrower_window")
    if not left and not right:
        raise Unsupported("no_occurrence_in_window")
    if not left or not right:
        raise Unsupported("sunrise_models_disagree")
    first, second = left[0], right[0]
    compare = ("identity", "sunrise_dates", "selected_date")
    if any(first[key] != second[key] for key in compare):
        raise Unsupported("sunrise_models_disagree")
    if first["selected_date"] is None or second["selected_date"] is None:
        raise Unsupported(first["reason"])
    if first["identity"] is None:
        raise Unsupported("unsupported_month_calculation")

    interval_start, interval_end = [datetime.fromisoformat(first[key]) for key in ("start", "end")]
    lower = interval_start.astimezone(DELHI).date()
    upper = interval_end.astimezone(DELHI).date()
    chosen = date.fromisoformat(first["selected_date"])
    origins = delhi_observations() if references is None else references
    for day, ordinal in origins:
        observed_day = date.fromisoformat(day)
        if lower <= observed_day <= upper:
            if any(astronomy.at_sunrise(observed_day, model)["ordinal"] != ordinal
                   for model in MODELS):
                raise Unsupported("delhi_reference_disagreement")

    # Inspect the full spread between Delhi sunrise hypotheses at every endpoint.
    # The extra solver bracket accounts for the rounded-up transition endpoints.
    day = lower
    margins = []
    endpoints = publisher_endpoints() if endpoints is None else endpoints
    entry = edge_window(interval_start, rule.ordinal, endpoints)
    exit = edge_window(interval_end, rule.ordinal % 30 + 1, endpoints)
    while day <= upper:
        dawns = sorted(astronomy.sunrise(day, model) for model in MODELS)
        for earliest, latest in (entry, exit):
            if (dawns[0] - latest).total_seconds() <= DATE_GUARD_SECONDS and (
                    dawns[-1] - earliest).total_seconds() >= -DATE_GUARD_SECONDS:
                raise Unsupported("boundary_uncertainty")
        if day == chosen:
            margins = [(dawns[0] - entry[1]).total_seconds(),
                       (exit[0] - dawns[-1]).total_seconds()]
        day += timedelta(days=1)
    if not margins or min(margins) <= DATE_GUARD_SECONDS:
        raise Unsupported("boundary_uncertainty")

    return dict(first, guarded_policy=POLICY, model_profiles=[p["profile"] for p in previews],
                minimum_margin_seconds=round(min(margins), 3))


def development_profile():
    from .astronomy import METADATA

    return dict(policy=POLICY, guard_seconds=DATE_GUARD_SECONDS, models=list(MODELS),
                references=fingerprints(), publisher_timing=PUBLISHER_TOLERANCE_SECONDS,
                ephemeris=json.loads(METADATA.read_text(encoding="utf-8")))


class GuardedCalendar:
    def __init__(self, kernel):
        self.kernel = kernel
        self.specification = development_profile()
        # Verify the pinned inputs at startup, before the service accepts a preview.
        with Astronomy(kernel):
            pass

    def __call__(self, rule, start, end):
        if self.specification != development_profile():
            raise Unsupported("reference_profile_changed")
        with Astronomy(self.kernel) as astronomy:
            return guarded_occurrence(astronomy, rule, start, end)
