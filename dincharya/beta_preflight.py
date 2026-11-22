"""Fail-closed, offline planning guard for a future personal-beta deployment.

This module does not start services, access secrets, or authorize messaging.
It validates a proposed *inert* runtime plan, not operational readiness.
"""
from pathlib import Path
import json
import re

_SHA = re.compile(r"sha256:[0-9a-f]{64}\\Z")
_REQUIRED = frozenset({"postgres", "n8n", "gateway", "scheduler", "worker"})
_FORBIDDEN = frozenset({"telegram_token", "bot_token", "password", "secret", "api_key",
                        "command_key", "tick_key", "review_key", "whatsapp_token"})


def validate_plan(value):
    if type(value) is not dict:
        raise ValueError("Beta plan must be an object")
    expected = {"version", "stage", "telegram_egress", "whatsapp",
                "startup", "source_adopted", "services",
                "database", "monitoring", "backup"}
    if set(value) != expected or value["version"] != 1:
        raise ValueError("Invalid beta plan structure")
    if value["stage"] != "preparation":
        raise ValueError("Only offline preparation plans are permitted")
    if value["telegram_egress"] is not False or value["whatsapp"] is not False:
        raise ValueError("All messaging channels must remain disabled")
    if value["startup"] is not False or value["source_adopted"] is not False:
        raise ValueError("Runtime startup or source promotion not approved")

    services = value["services"]
    if type(services) is not dict or set(services) != _REQUIRED:
        raise ValueError("Exactly one of each runtime service is required")
    for name, service in services.items():
        if type(service) is not dict or set(service) != {"image", "enabled"}:
            raise ValueError("Invalid service configuration: " + name)
        if service["enabled"] is not False:
            raise ValueError("Service activation prohibited")
        # The image may be 'pending' while exact image provenance is reviewed.
        image = service["image"]
        if type(image) is not str or (image != "pending" and not _SHA.fullmatch(image)):
            raise ValueError("Image must be pending or exact immutable digest")

    database = value["database"]
    if type(database) is not dict or set(database) != {"name", "fresh", "isolated", "migration_adopted"}:
        raise ValueError("Invalid database plan")
    if (not isinstance(database["name"], str)
            or database["name"] != "dincharya_personal_beta"
            or database["fresh"] is not True or database["isolated"] is not True
            or database["migration_adopted"] is not False):
        raise ValueError("Beta database must be fresh, separate and not migrated")
    monitor = value["monitoring"]
    if (type(monitor) is not dict or set(monitor) != {"independent", "verified"}
            or type(monitor["independent"]) is not bool
            or monitor["verified"] is not False):
        raise ValueError("Unverified external monitoring must not be claimed")
    backup = value["backup"]
    if (type(backup) is not dict or set(backup) != {"off_device", "encrypted", "restore_verified"}
            or any(type(v) is not bool for v in backup.values())
            or backup["restore_verified"] is not False):
        raise ValueError("Unverified backup restore must not be claimed")

    def reject_secrets(node):
        if isinstance(node, dict):
            for key, val in node.items():
                if key.lower() in _FORBIDDEN:
                    raise ValueError("Secret fields are not allowed in beta plan")
                reject_secrets(val)
        elif isinstance(node, list):
            for val in node:
                reject_secrets(val)

    reject_secrets(value)
    return True


def verify_file(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8192:
        raise ValueError("Unsafe plan file")
    return validate_plan(json.loads(path.read_text(encoding="utf-8")))


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", nargs="?", default="docs/beta-runtime-plan.json")
    args = parser.parse_args()
    try:
        verify_file(args.plan)
    except (ValueError, OSError, json.JSONDecodeError):
        parser.exit(1, "FAIL: beta plan is not inert or valid\\n")
    print("PASS: offline beta planning flags are disabled; NOT runtime authorization")


if __name__ == "__main__":
    main()
