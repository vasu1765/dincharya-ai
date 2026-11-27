"""Signed recorded-update dispatcher for the fresh rehearsal database."""
from datetime import datetime, timezone
import hmac
import re
import time
from uuid import UUID

from dincharya.beta_preview import owner_message, preview
from dincharya.lunar_service import sign


class BetaDispatcher:
    def __init__(self, connect, key, *, clock=time.time):
        if not isinstance(key, str) or len(key) < 32:
            raise ValueError("Separate rehearsal signing key required")
        self.connect, self.key, self.clock = connect, key, clock

    def handle(self, value, signature):
        now = self.clock()
        if (not isinstance(value, dict) or set(value) != {"command", "nonce", "timestamp"}
                or type(value["timestamp"]) is not int or abs(now - value["timestamp"]) > 60
                or not isinstance(value["nonce"], str) or not 1 <= len(value["nonce"]) <= 80
                or not isinstance(signature, str) or not signature.isascii()
                or not hmac.compare_digest(sign(self.key, "command", value), signature)):
            return {"status": "denied"}
        try:
            update = value["command"]["update"]
            if set(value["command"]) != {"operation", "update"} or value["command"]["operation"] != "beta_update":
                return {"status": "denied"}
            request = update["update_id"]
            if type(request) is not int or request <= 0:
                return {"status": "denied"}
            if "callback_query" in update:
                callback = update["callback_query"]
                chat, sender = callback["message"]["chat"], callback["from"]
                if (chat["type"] != "private" or sender["is_bot"] is not False
                        or any(type(x) is not int or x != 101 for x in (chat["id"], sender["id"]))):
                    return {"status": "denied"}
                action, token = callback["data"].split("/")
                if action not in ("confirm", "cancel", "apply"):
                    return {"status": "denied"}
                if action == "apply":
                    sql, args = "SELECT beta.apply_change(%s,%s)", (101, UUID(token))
                else:
                    sql, args = "SELECT beta.decide(%s,%s,%s)", (101, UUID(token), action == "confirm")
                result = {}
            elif (match := re.fullmatch(r"/(pause|resume|cancel) ([0-9a-f-]{36})",
                                        owner_message(update, 101).get("text", ""))):
                sql = "SELECT beta.review_change(%s,%s,%s,%s)"
                args = (101, request, UUID(match[2]), match[1])
                result = {"status": "change_preview", "action": match[1], "rule": match[2],
                          "requires_confirmation": True}
            else:
                result = preview(update, 101, datetime.fromtimestamp(now, timezone.utc))
                desired = result["activity"]
                rule = desired["recurrence_rule"]
                sql = "SELECT beta.draft(%s,%s,%s,%s,%s::date,%s::time,%s::integer[])"
                args = (101, request, desired["title"], rule["frequency"], rule["start_date"],
                        desired["start_time"], result["offset_minutes"])
        except (KeyError, ValueError, AttributeError, TypeError):
            return {"status": "denied"}
        with self.connect() as conn:
            identity = conn.execute("SELECT current_database(),current_user,session_user").fetchone()
            if identity != ("dincharya_beta_rehearsal", "beta_gateway", "beta_gateway"):
                raise ValueError("Rehearsal gateway identity required")
            response = conn.execute(sql, args).fetchone()[0]
        if result:
            return {**result, "token": str(response)}
        return {"status": response}
