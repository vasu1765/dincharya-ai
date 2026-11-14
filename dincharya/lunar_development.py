"""Isolated astronomical lunar review through the existing scoped PostgreSQL API."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import secrets
from threading import Lock
import time as wall
from uuid import UUID, uuid5

from dincharya.lunar_intent import Clarify, EXAMPLE, parse_request
from dincharya.lunar_service import NAMESPACE, canonical
from prototypes.panchang.astronomy import DELHI, Unsupported
from prototypes.panchang.recurrence import LunarRule


@dataclass
class Review:
    expires: float
    data: dict
    reply: str
    decision: str | None = None
    result: dict | None = None


class DevelopmentLunar:
    """Pending reviews expire on restart. Durable effects use stable SQL action IDs."""

    def __init__(self, owner, calculator, calendar, profile, *, clock=wall.time):
        self.owner = owner
        self.calculator = calculator
        self.calendar = calendar
        self.profile = profile
        self.clock = clock
        self.pending = {}
        self.lock = Lock()

    def _fail(self, reason, status="withheld"):
        return dict(status=status, reply=f"Date withheld / तिथि रोकी गई ({reason}).")

    def _display(self, plan):
        row, intent = plan["row"], plan["intent"]
        i = row["identity"]
        dates = ", ".join(row["sunrise_dates"])
        return (f'{intent["title"]}\n{i["month"]} {i["paksha"]} tithi {i["tithi"]}, '
                f'{i["convention"]}, {i["intercalation"]}; repeat: {intent["rule"]["repeated"]}.\n'
                f'Delhi sunrise dates: {dates}\n'
                f'Appointment: {row["selected_date"]} at {intent["time"]} IST. '
                f'Purpose: {intent["purpose"].replace("_", " ")}. '
                'One occurrence, reminder at start. Development database only.')

    def _selection(self, intent):
        rule = LunarRule(**intent["rule"])
        start, end = (date.fromisoformat(intent[key]) for key in ("start", "end"))
        candidate = self.calendar(rule, start, end)
        selected = date.fromisoformat(candidate["selected_date"])
        # A fixed window around the selected date produces stable evidence even
        # when a user describes the same appointment using a different window.
        row = self.calendar(rule, selected - timedelta(days=2), selected + timedelta(days=3))
        keys = ("identity", "selected_date", "sunrise_dates")
        if any(row[key] != candidate[key] for key in keys):
            raise Unsupported("date_selection_changed")
        instant = datetime.combine(selected, time.fromisoformat(intent["time"]), DELHI)
        if instant.timestamp() <= self.clock():
            raise Unsupported("appointment_is_in_the_past")
        return dict(intent=intent, row=row)

    def _verify(self, plan):
        intent = plan["intent"]
        row = plan["row"]
        day = date.fromisoformat(row["selected_date"])
        rule = LunarRule(**intent["rule"])
        checked = self.calendar(rule, day - timedelta(days=2), day + timedelta(days=3))
        instant = datetime.combine(day, time.fromisoformat(intent["time"]), DELHI)
        if checked != row or instant.timestamp() <= self.clock():
            raise Unsupported("preview_stale")

    def _issue(self, data, reply, status):
        if len(self.pending) >= 128:
            return self._fail("too_many_pending_reviews")
        handle = secrets.token_urlsafe(18)
        self.pending[handle] = Review(self.clock() + 1800, data, reply)
        return dict(status=status, reply=reply, review=handle)

    def handle(self, command):
        # Serialize review transitions and the astronomy cache. Do not use an
        # update ID for durable idempotency because Telegram redelivers clicks.
        if not self.lock.acquire(timeout=3):
            return dict(status="busy", reply="A lunar review is running. Retry the same request or button.")
        try:
            now = self.clock()
            self.pending = {key: value for key, value in self.pending.items() if now < value.expires}
            operation = command["operation"]
            if operation == "draft_lunar":
                if set(command) != {"operation", "text"}:
                    return self._fail("invalid_request")
                try:
                    plan = self._selection(parse_request(command["text"]))
                    plan["attempt"] = secrets.token_urlsafe(18)
                except Clarify as exc:
                    return dict(status="clarify", reply=f"{exc}\n{EXAMPLE}")
                except Unsupported as exc:
                    return self._fail(str(exc))
                return self._issue(plan, self._display(plan) +
                                   "\nConfirm rule / नियम की पुष्टि, then review the appointment.",
                                   "rule_preview")
            if set(command) != {"operation", "review"} or not isinstance(command["review"], str):
                return self._fail("invalid_review")
            handle = command["review"]
            review = self.pending.get(handle)
            if review is None:
                return self._fail("preview_expired_or_unavailable")
            choice = "approve" if operation == "confirm_lunar_draft" else "reject"
            if review.decision and review.decision != choice:
                return self._fail("already_decided")
            if review.result is not None:
                nested = review.result.get("review")
                if nested and nested not in self.pending:
                    return self._fail("preview_expired_or_unavailable")
                return review.result
            if "request" in review.data:
                if choice == "approve":
                    try:
                        self._verify(review.data["plan"])
                    except Unsupported:
                        return self._fail("preview_stale")
                if self.clock() >= review.expires:
                    return self._fail("preview_expired_or_unavailable")
                review.decision = choice
                result = self._decide_occurrence(review.data, choice)
            elif choice == "reject":
                review.decision = choice
                result = dict(status="rejected", reply="Draft cancelled / प्रस्ताव रद्द।")
            else:
                try:
                    self._verify(review.data)
                except Unsupported:
                    return self._fail("preview_stale")
                if self.clock() >= review.expires:
                    return self._fail("preview_expired_or_unavailable")
                if len(self.pending) >= 128:
                    return self._fail("too_many_pending_reviews")
                review.decision = choice
                result = self._approve_rule(review.data)
            review.result = result
            return result
        finally:
            self.lock.release()

    def _approve_rule(self, plan):
        intent, row = plan["intent"], plan["row"]
        rule = dict(intent["rule"], profile=self.profile)
        # The same appointment re-entered under another update/window resolves
        # to the same series. Different recurrence semantics require review.
        event_key = dict(identity=row["identity"], title=intent["title"], time=intent["time"])
        series = uuid5(NAMESPACE, "development/" + canonical(event_key))
        request = self.owner.propose_series(uuid5(series, "rule-proposal"), series,
                                            intent["purpose"], 0, rule)
        reviewed = self.owner.inspect_request(request)
        if reviewed["status"] == "pending":
            decided = self.owner.decide(uuid5(series, "rule-approve"), request, "approve",
                                        reviewed["fingerprint"], reviewed=True)
            if decided["status"] != "approved":
                return self._fail("rule_approval_unavailable")
        elif reviewed["status"] != "approved":
            return self._fail("rule_approval_unavailable")
        repeated = len(row["sunrise_dates"]) > 1
        evidence = dict(status="selected", month_status="supported", date_gate="pass",
                        kshaya=False, ambiguous=False, skipped=False, repeated=repeated,
                        selection=row["selected_date"], birth_basis=rule["birth_basis"],
                        repetition_policy=rule["repeated"], interval_start=row["start"],
                        interval_end=row["end"], policy=row["guarded_policy"],
                        model_profiles=row["model_profiles"], sunrise_dates=row["sunrise_dates"],
                        minimum_margin_seconds=row["minimum_margin_seconds"])
        occurrence = UUID(str(self.calculator.record_calculation(
            uuid5(series, "calculation"), series, 1, row["identity"], self.profile, evidence,
            date.fromisoformat(row["selected_date"]))))
        snapshot = self.owner.inspect_occurrence(occurrence)["occurrence"]
        if snapshot.get("cancelled"):
            return self._fail("appointment_was_cancelled")
        if snapshot["event_id"] is not None:
            return dict(status="already_scheduled", reply="Appointment already recorded.",
                        occurrence=str(occurrence))
        desired = dict(date=row["selected_date"], title=intent["title"], start_time=intent["time"])
        # Key by the review attempt so a rejected occurrence can be proposed
        # again without changing the underlying series or logical occurrence.
        request = self.owner.propose_occurrence(
            uuid5(occurrence, "select/" + plan["attempt"]), occurrence, "select", 1,
            snapshot["revision"], snapshot["observation"], desired)
        reviewed = self.owner.inspect_request(request)
        conflict_count = len(reviewed.get("conflicts", ()))
        result = self._issue(dict(plan=plan, request=request, fingerprint=reviewed["fingerprint"],
                                  occurrence=str(occurrence)),
                             self._display(plan) + f"\nExisting appointments on that date: {conflict_count}. "
                             "Confirm appointment / समय की पुष्टि।",
                             "occurrence_preview")
        return dict(result, occurrence=str(occurrence))

    def _decide_occurrence(self, data, choice):
        action = uuid5(NAMESPACE, f'development/decision/{data["request"]}/{choice}')
        result = self.owner.decide(action, data["request"], choice, data["fingerprint"], reviewed=True)
        replies = {
            "approved": "Appointment recorded in the development database.",
            "rejected": "Appointment cancelled / प्रस्ताव रद्द।",
            "conflict": "Schedule conflict. No appointment was created.",
        }
        return dict(status=result["status"], occurrence=data["occurrence"],
                    reply=replies.get(result["status"], "Appointment unavailable; inspect status."))
