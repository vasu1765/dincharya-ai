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
        self.recurring = None
        self.historical = None

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
                'Reminder at start. Development database only.')

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
        if "annual_year" in intent:
            checked = self._selection(intent)["row"]
        else:
            checked = self.calendar(rule, day - timedelta(days=2), day + timedelta(days=3))
        instant = datetime.combine(day, time.fromisoformat(intent["time"]), DELHI)
        if checked != row or instant.timestamp() <= self.clock():
            raise Unsupported("preview_stale")

    def _annual_rule(self, intent):
        year = intent["annual_year"]
        current = datetime.fromtimestamp(self.clock(), DELHI).year
        if not current <= year <= min(current + 5, 2099):
            raise Clarify("Choose a start year from this year through the next five years.")
        rule = LunarRule(**intent["rule"])
        if rule.intercalation == "both":
            raise Clarify("Choose ordinary or Adhika for an annual rule.")
        reply = (f'{intent["title"]}\nAnnual Delhi lunar rule from {year}, at {intent["time"]} IST.\n'
                 f'{rule.month} {rule.paksha} tithi {rule.tithi}, {rule.convention}, '
                 f'{rule.intercalation}; repeat: {rule.repeated}.\n'
                 'Confirm rule / नियम की पुष्टि। Each future appointment needs its own confirmation.')
        return self._issue({"annual_intent": intent}, reply, "rule_preview")

    def _annual_command(self, command, operation):
        if operation == "list_lunar_annual":
            if set(command) != {"operation", "after"}:
                return self._fail("invalid_request")
            after = UUID(command["after"]) if command["after"] else None
            items = self.owner.list_annual_rules(after)
            lines = [f'{row["series_id"]}  {row["title"]}  from {row["start_year"]}'
                     + ("" if row["enabled"] else " (cancelled)") for row in items]
            if len(items) == 10:
                lines.append(f'Next page /lunar_rules {items[-1]["series_id"]}')
            return dict(status="listed", reply="\n".join(lines) or "No annual lunar rules in this page.")

        resume = operation == "resume_lunar_annual"
        cancel_occurrence = operation == "cancel_lunar_annual_occurrence"
        required = {"operation", "series"} | ({"year"} if resume else
                                               {"occurrence"} if cancel_occurrence else set())
        if set(command) != required:
            return self._fail("invalid_request")
        series = UUID(command["series"])
        saved = self.owner.inspect_annual_rule(series)
        rule_info, metadata = saved["series"], saved["annual"]
        if operation == "status_lunar_annual":
            manifest = self.owner.inspect_series(series)["manifest"]
            lines = []
            for item in manifest:
                row = item["occurrence"]
                projected = item.get("projection") or {}
                calendar = projected.get("rule") or {}
                lines.append((calendar.get("start_date", "date unavailable"), row["id"]))
            state = "active" if rule_info["enabled"] else "cancelled"
            listing = "\n".join(f"{day}  {occurrence}" for day, occurrence in sorted(lines))
            reply = (f'{metadata["title"]}  {state}\nSeries {series}\n'
                     + (listing or "No active appointments."))
            return dict(status="inspected", series=str(series), reply=reply)
        if not rule_info["enabled"]:
            return self._fail("series_cancelled")
        control = None
        if resume and self.recurring:
            control = next((item for item in self.recurring.controls()["controls"]
                            if item["series_id"] == str(series)), None)
            if control and (control["mode"] != "manual" or control["state"] != "active"):
                return self._fail("automatic_or_inactive_rule")
        if resume:
            year = command["year"]
            current = datetime.fromtimestamp(self.clock(), DELHI).year
            if type(year) is not int or not max(current, metadata["start_year"]) <= year <= min(current + 5, 2099):
                return self._fail("annual_year_outside_review_window")
            rule = dict(rule_info["rule"])
            if rule.pop("profile") != self.profile:
                return self._fail("reference_profile_changed")
            intent = dict(rule=rule, title=metadata["title"], time=metadata["appointment_time"][:5],
                          purpose=rule_info["purpose"], start=date(year, 1, 1).isoformat(),
                          end=date(year + 1, 1, 1).isoformat(), annual_year=metadata["start_year"])
            if len(self.pending) >= 128:
                return self._fail("too_many_pending_reviews")
            try:
                plan = self._selection(intent)
            except Unsupported as exc:
                return self._fail(str(exc))
            plan["attempt"] = secrets.token_urlsafe(18)
            return self._prepare_occurrence(plan, series, rule_info["revision"], annual=True, control=control)

        if len(self.pending) >= 128:
            return self._fail("too_many_pending_reviews")
        action = UUID(bytes=secrets.token_bytes(16))
        if cancel_occurrence:
            occurrence = UUID(command["occurrence"])
            snapshot = self.owner.inspect_occurrence(occurrence)
            row = snapshot["occurrence"]
            if row["series_id"] != str(series) or row["cancelled"] or row["event_id"] is None:
                return self._fail("appointment_unavailable")
            request = self.owner.propose_occurrence(action, occurrence, "cancel", rule_info["revision"],
                                                    row["revision"], row["observation"], {})
            target = str(occurrence)
            day = snapshot["projection"]["rule"]["start_date"]
            reply = f'Cancel {metadata["title"]} on {day}?\nAppointment {target}'
        else:
            snapshot = self.owner.inspect_series(series)
            manifest = snapshot["manifest"]
            request = self.owner.propose_series_cancel(action, series, rule_info["revision"], manifest)
            target = str(series)
            dates = sorted(item["projection"]["rule"]["start_date"] for item in manifest)
            reply = (f'Cancel annual rule {metadata["title"]} and its {len(manifest)} active appointments?\n'
                     f'Series {target}\n' + ", ".join(dates))
        reviewed = self.owner.inspect_request(request)
        return self._issue(dict(request=request, fingerprint=reviewed["fingerprint"], occurrence=target,
                                annual=True, cancellation=True), reply, "cancellation_preview")

    def _approve_annual(self, intent, expires):
        # Ignore the entered start year when deriving the stable series ID.
        # The stored metadata detects incompatible start-year re-entry.
        rule = dict(intent["rule"], profile=self.profile)
        # The profile is revision metadata, not part of the logical series identity.
        identity = {name: value for name, value in intent["rule"].items() if name != "repeated"}
        key = dict(title=intent["title"], time=intent["time"], rule=identity)
        series = uuid5(NAMESPACE, "development-annual/" + canonical(key))
        result = self.owner.approve_annual_rule(
            series, uuid5(series, "rule-proposal"), uuid5(series, "rule-approve"),
            intent["purpose"], rule, intent["annual_year"], intent["title"], intent["time"],
            datetime.fromtimestamp(expires, DELHI))
        if result["status"] != "approved":
            return self._fail(result["status"])
        return dict(status="annual_rule_approved", series=str(series),
                    reply=f'Annual rule approved.\nSeries {series}\n'
                    f'Preview a year with /lunar_year {series} {intent["annual_year"]}')

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
            if operation in {"historical_panchang", "draft_historical_anniversary"}:
                if self.historical is None or set(command) != {"operation", "text"}:
                    return self._fail("historical_development_unavailable")
                from dincharya.historical_panchang import historical_text

                try:
                    if operation == "draft_historical_anniversary":
                        return self.historical.anniversary(self.recurring, command["text"])
                    event = historical_text(command["text"])
                    return dict(status="historical_answer", reply=self.historical.display(event, self.historical.read(event)))
                except Clarify as error:
                    return dict(status="clarify", reply=str(error))
                except Unsupported as error:
                    return self._fail(str(error))
            if operation in {"list_lunar_annual", "resume_lunar_annual", "cancel_lunar_annual",
                             "status_lunar_annual", "cancel_lunar_annual_occurrence"}:
                return self._annual_command(command, operation)
            if operation in {"draft_recurring", "recurring_rules", "review_recurring_change",
                             "review_recurring_adoption", "project_tick", "reserve_recurring_alert", "recurring_health"}:
                if self.recurring is None:
                    return self._fail("recurring_development_disabled")
                try:
                    if operation == "draft_recurring" and set(command) == {"operation", "text"}:
                        return self.recurring.draft(command["text"])
                    if operation == "project_tick" and set(command) == {"operation"}:
                        result = self.recurring.project()
                        if self.historical:
                            from dincharya.recurring import call

                            call(self.owner, "mark_recurring_success", ())
                        return result
                    if operation == "recurring_health" and self.historical and set(command) == {"operation"}:
                        from dincharya.recurring import call

                        health = call(self.owner, "recurring_health", ())
                        return dict(status="health", health=health, reply=(
                            f'Last projection · {health["last_projection"] or "unrecorded"}\n'
                            f'Due {health["due"]} · Sending {health["sending"]} · '
                            f'Quarantined {health["uncertain"]} · Dead {health["dead"]}\n'
                            f'Last confirmed slot due · {health["last_confirmed_due"] or "unrecorded"}\n'
                            + "\n".join(f'Slot {s["id"]} · {s["occurrence_date"]} · offset {s["offset_minutes"]} minutes'
                                        for s in health["quarantine"])))
                    if operation == "reserve_recurring_alert" and set(command) == {"operation"}:
                        return self.recurring.reserve_alert()
                    if operation == "recurring_rules" and set(command) == {"operation"}:
                        info = self.recurring.controls()
                        lines = [f'{x["id"]} · {x["title"]} · {x["mode"]} · {x["state"]}' for x in info["controls"]]
                        lines += [f'Withheld {x["target_year"]}: {x["reason"]} ({x["control"]})'
                                  for x in info["withheld"]]
                        return dict(status="listed", reply="\n".join(lines)[:3900] or "No reviewed rules.")
                    if operation == "review_recurring_change" and set(command) == {
                            "operation", "control", "change", "policy"}:
                        return self.recurring.change_preview(self.recurring.controls()["controls"], command)
                    if operation == "review_recurring_adoption" and set(command) == {"operation", "series", "mode"}:
                        return self.recurring.adopt_preview(command["series"], command["mode"])
                except Clarify as error:
                    return dict(status="clarify", reply=str(error))
                return self._fail("invalid_request")
            if operation == "draft_lunar":
                if set(command) != {"operation", "text"}:
                    return self._fail("invalid_request")
                try:
                    intent = parse_request(command["text"])
                    if "annual_year" in intent:
                        return self._annual_rule(intent)
                    plan = self._selection(intent)
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
                if choice == "approve" and "plan" in review.data:
                    try:
                        self._verify(review.data["plan"])
                    except Unsupported:
                        return self._fail("preview_stale")
                if self.clock() >= review.expires:
                    return self._fail("preview_expired_or_unavailable")
                review.decision = choice
                result = self._decide_occurrence(review, choice)
            elif choice == "reject":
                review.decision = choice
                result = dict(status="rejected", reply="Draft cancelled / प्रस्ताव रद्द।")
            elif "recurring" in review.data or "recurring_change" in review.data:
                review.decision = choice
                if "recurring" in review.data:
                    if review.data["recurring"][3].get("historical"):
                        if not self.historical or not self.historical.verify(review.data["recurring"][3]):
                            return self._fail("historical_preview_changed")
                    result = self.recurring.approve(review.data["recurring"], review.expires)
                else:
                    result = self.recurring.change(review.data["recurring_change"], review.expires)
            elif "annual_intent" in review.data:
                review.decision = choice
                result = self._approve_annual(review.data["annual_intent"], review.expires)
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
        return self._prepare_occurrence(plan, series, 1)

    def _calculation(self, plan, series, revision, annual):
        intent, row = plan["intent"], plan["row"]
        rule = intent["rule"]
        repeated = len(row["sunrise_dates"]) > 1
        evidence = dict(status="selected", month_status="supported", date_gate="pass",
                        kshaya=False, ambiguous=False, skipped=False, repeated=repeated,
                        selection=row["selected_date"], birth_basis=rule["birth_basis"],
                        repetition_policy=rule["repeated"], interval_start=row["start"],
                        interval_end=row["end"], policy=row["guarded_policy"],
                        model_profiles=row["model_profiles"], sunrise_dates=row["sunrise_dates"],
                        minimum_margin_seconds=row["minimum_margin_seconds"])
        calculation = ("annual-calculation/" + canonical(row["identity"])) if annual else "calculation"
        return UUID(str(self.calculator.record_calculation(
            uuid5(series, calculation), series, revision, row["identity"], self.profile, evidence,
            date.fromisoformat(row["selected_date"]))))
    def _prepare_occurrence(self, plan, series, revision, *, annual=False, control=None):
        if len(self.pending) >= 128:
            return self._fail("too_many_pending_reviews")
        intent, row = plan["intent"], plan["row"]
        occurrence = self._calculation(plan, series, revision, annual)
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
            uuid5(occurrence, "select/" + plan["attempt"]), occurrence, "select", revision,
            snapshot["revision"], snapshot["observation"], desired)
        reviewed = self.owner.inspect_request(request)
        conflict_count = len(reviewed.get("conflicts", ()))
        details = self._display(plan)
        if control:
            from dincharya.recurring import policy_name
            offsets = control["offsets"]
            details = details.replace("Reminder at start.", f"Manual · {policy_name(offsets)} · offsets {offsets} minutes.")
        result = self._issue(dict(plan=plan, request=request, fingerprint=reviewed["fingerprint"],
                                  occurrence=str(occurrence), annual=annual, control=control, series=str(series)),
                             details + (f"\nAnnual series {series}." if annual else "")
                             + f"\nExisting appointments on that date: {conflict_count}. "
                             "Confirm appointment / समय की पुष्टि।",
                             "occurrence_preview")
        return dict(result, occurrence=str(occurrence))

    def _decide_occurrence(self, review, choice):
        data = review.data
        action = uuid5(NAMESPACE, f'development/decision/{data["request"]}/{choice}')
        if data.get("control"):
            from dincharya.recurring import call
            control = data["control"]
            result = call(self.owner, "decide_recurring_manual", (
                UUID(control["id"]), control["revision"], action, data["request"], choice,
                data["fingerprint"], datetime.fromtimestamp(review.expires, DELHI)))
        elif data.get("annual"):
            if (self.recurring and data.get("series") and
                    any(row["series_id"] == data["series"] for row in self.recurring.controls()["controls"])):
                return self._fail("approval_mode_changed")
            result = self.owner.decide_annual_review(action, data["request"], choice, data["fingerprint"],
                                                    datetime.fromtimestamp(review.expires, DELHI))
        else:
            result = self.owner.decide(action, data["request"], choice, data["fingerprint"], reviewed=True)
        replies = {
            "approved": "Appointment recorded in the development database.",
            "rejected": "Appointment cancelled / प्रस्ताव रद्द।",
            "conflict": "Schedule conflict. No appointment was created.",
        }
        if data.get("cancellation"):
            replies["approved"] = "Cancellation approved. Appointment and delivery history are retained."
            replies["rejected"] = "Cancellation proposal discarded."
        return dict(status=result["status"], occurrence=data["occurrence"],
                    reply=replies.get(result["status"], "Appointment unavailable; inspect status."))
