"""Cycle 5 recurring rule review and rolling projection in the isolated service."""
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4, uuid5

from dincharya.lunar_intent import Clarify, DIGITS
from dincharya.lunar_service import NAMESPACE, canonical
from prototypes.panchang.astronomy import DELHI, Unsupported

from dincharya.recurring_intent import (CIVIL, DAY_ALIASES, DAYS, NOTIFICATION_EDIT,
                                       notification, parse_recurring, policy_name)

REVIEW_WINDOW_DAYS = 400


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
        return self.draft_spec(mode, offsets, spec, now)

    def draft_spec(self, mode, offsets, spec, now, *, prefix=""):
        eligible = "No safe occurrence in the rolling window."
        warnings = []
        if spec["kind"] == "lunar":
            scheduled_clock = spec["time"]
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
            scheduled_clock = desired["start_time"]
            rule = desired["recurrence_rule"]
            label = f'{desired["title"]} · Gregorian {rule["frequency"]}'
            if rule["frequency"] == "weekly":
                label += f' {DAYS[rule["weekdays"][0]-1].title()}'
            if rule["frequency"] == "yearly":
                label += f' on {rule["months"][0]:02d}-{rule["month_days"][0]:02d}'
            eligible = f'{desired["recurrence_rule"]["start_date"]} at {desired["start_time"]}'
        details = (f"{label}\n{mode} · {policy_name(offsets)} · offsets {offsets} minutes\n"
                   f"Asia/Kolkata · appointment time {scheduled_clock}\nNext · {eligible}")
        if warnings:
            details += "\nWithheld: " + "; ".join(warnings)
        # Gregorian intent changes require a separate approved edit, not an
        # accidental second rule from a new preview with different offsets.
        name = {k: v for k, v in spec.items() if k != "historical"} if spec["kind"] == "lunar" else {
            **spec["desired"], "recurrence_rule": {k: v for k, v in spec["desired"]["recurrence_rule"].items()
                                                   if k != "start_date" or rule["frequency"] == "once"}}
        key = uuid5(NAMESPACE, "recurring/" + canonical(name))
        reply = f"{prefix}\n\n{details}" if prefix else details
        return self.dev._issue(dict(recurring=(key, mode, offsets, spec)), reply, "rule_preview")

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
                    if result["status"] == "restore_review_required":
                        raise Unsupported("restore_review_required")
                except Unsupported as error:
                    if str(error) == "appointment_is_in_the_past":
                        continue
                    call(self.owner, "recurring_withhold", (key, version, year, str(error)[:100]))
                    alerts.append(f"{key} · {year} · {error}")
        return dict(status="projected", alerts=alerts, reply="\n".join(alerts) or "Projection check complete.")
