"""Simulate a private Telegram text update. No transport or persistence."""
from datetime import datetime
import json
import sys
from zoneinfo import ZoneInfo

from dincharya.recurring_intent import parse_recurring, policy_name


def preview(update, owner, now):
    if type(owner) is not int or not 0 < owner < 2**63:
        raise ValueError("Invalid owner")
    message = update.get("message") if isinstance(update, dict) else None
    if not isinstance(message, dict):
        raise ValueError("Private text message required")
    chat, sender = message.get("chat"), message.get("from")
    if not (isinstance(chat, dict) and isinstance(sender, dict) and
            chat.get("type") == "private" and sender.get("is_bot") is False and
            all(type(item.get("id")) is int and item["id"] == owner for item in (chat, sender))):
        raise ValueError("Private owner message required")
    if now.utcoffset() is None:
        raise ValueError("Timezone-aware clock required")
    local = now.astimezone(ZoneInfo("Asia/Kolkata"))
    mode, offsets, spec = parse_recurring(message.get("text"), local.date(), local, civil_only=True)
    return {"status": "preview", "requires_confirmation": True, "activity": spec["desired"],
            "approval_mode": mode, "notification": policy_name(offsets), "offset_minutes": offsets}


if __name__ == "__main__":
    # Fixed synthetic identity for recorded updates only.
    print(json.dumps(preview(json.load(sys.stdin), 101, datetime.now(ZoneInfo("Asia/Kolkata"))),
                     ensure_ascii=False))
