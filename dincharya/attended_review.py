"""Offline rendering of the accepted dispatcher's two one-off Gate 1 previews.

Returns a Telegram-shaped payload for inspection. This module has no client.
"""
from datetime import date, time
from uuid import UUID

from dincharya.recurring_intent import policy_name


def appointment_preview(result):
    if result.get("status") != "preview" or result.get("requires_confirmation") is not True:
        raise ValueError("An unconfirmed scheduling preview is required")
    activity = result["activity"]
    rule = activity["recurrence_rule"]
    offsets = result["offset_minutes"]
    if (rule.get("calendar_system") != "gregorian" or rule.get("frequency") != "once"
            or rule.get("interval_count") != 1 or set(rule) != {"calendar_system", "frequency", "interval_count", "start_date"}
            or activity.get("timezone") != "Asia/Kolkata" or result.get("approval_mode") != "automatic"
            or type(offsets) is not list or any(type(x) is not int for x in offsets)
            or offsets not in ([], [0]) or result.get("notification") != policy_name(offsets)):
        raise ValueError("Outside the attended one-off rehearsal scope")
    title = activity["title"]
    if not isinstance(title, str) or not title.isprintable() or not 1 <= len(title) <= 80:
        raise ValueError("Invalid activity title")
    day = date.fromisoformat(rule["start_date"])
    clock = time.fromisoformat(activity["start_time"])
    if clock.strftime("%H:%M") != activity["start_time"]:
        raise ValueError("Expected local hour and minute")
    token = str(UUID(result["token"]))
    notification = "One reminder at the start" if offsets else "No reminder"
    return {"text": f"Schedule {title}?\nOnce · {day} at {clock:%H:%M} Asia/Kolkata\n{notification}",
            "reply_markup": {"inline_keyboard": [[
                {"text": "Confirm", "callback_data": "confirm/" + token},
                {"text": "Cancel", "callback_data": "cancel/" + token}]]}}
