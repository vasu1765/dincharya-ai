#!/usr/bin/env python3
"""Create or validate a review package for explicit repository-owned inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "vasu1765/dincharya-ai"
MIGRATIONS = (
    "0001_gregorian_occurrences", "0002_occurrence_reminders", "0003_managed_legacy_boundary",
    "0004_telegram_receipts", "0005_synthetic_reconciliation", "0006_synthetic_lunar_approval",
    "0007_lunar_calculation_binding", "0008_lunar_projection_trigger_path",
    "0009_lunar_delivery_status", "0010_synthetic_annual_lunar_rules",
    "0011_synthetic_notification_slots", "0012_synthetic_recurring_automation",
    "0013_synthetic_recurrence_health",
)
CANDIDATES = {
    "tests/integration/m2h_development_schema.sql": ("database_schema", "Invented isolated application schema"),
    "tests/integration/compose.json": ("application_configuration", "Version-pinned disposable services"),
    "telegram-gateway/requirements-m2g.txt": ("application_configuration", "Gateway dependencies for rebuild"),
    "prototypes/panchang/requirements.txt": ("application_configuration", "Hash-pinned astronomical dependencies"),
    "workflows/m2g-lunar-acceptance.json": ("current_workflow", "Repository-owned native signed relay"),
    "dincharya/lunar_service.py": ("security_sensitive_code", "Request signer verification and privileged dispatch"),
    "scripts/check-safe-source.py": ("security_sensitive_code", "Explicit safe-file admission check"),
    **{f"database/migrations/{name}.sql": ("database_migration", "Ordered additive SQL") for name in MIGRATIONS},
}
RECORDS = (
    ("legacy-current", "current_workflow", "archived", "Four current versions recorded in repository evidence"),
    ("legacy-published", "published_workflow", "awaiting_review", "Publication identity is distinct from current"),
    ("legacy-history", "historical_workflow", "archived", "94 versions recorded. Historical bodies are outside this review."),
    ("legacy-code", "executable_code_node", "excluded", "Seven bodies require separate read and execution authorization"),
    ("legacy-state", "runtime_state", "excluded", "Scheduler state, credentials and volumes are outside reconstruction"),
    ("original-schema", "database_schema", "awaiting_review", "Exact Cycle 4 WSL acceptance is scoped and preserved"),
    ("old-manifest", "historical_provenance", "archived", "Original index unavailable. Existing reports preserved."),
)


def read_source(name):
    path = ROOT / name
    if name not in CANDIDATES or path.resolve() != path or not path.is_file():
        raise ValueError("Expected an explicitly registered repository artifact")
    return path.read_bytes()


def validate_native_workflow(data):
    workflow = json.loads(data)
    nodes = workflow.get("nodes")
    expected = {"n8n-nodes-base.webhook", "n8n-nodes-base.httpRequest"}
    if (not isinstance(nodes, list) or len(nodes) != 2 or {node.get("type") for node in nodes} != expected
            or any(node.get("credentials") for node in nodes) or workflow.get("active") is not False):
        raise ValueError("Only the inactive native fixture relay belongs in this package")


def propose(commit):
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("Require an exact Git commit for the starting checkpoint")
    entries = []
    for name, (category, purpose) in sorted(CANDIDATES.items()):
        data = read_source(name)
        if category == "current_workflow":
            validate_native_workflow(data)
        entries.append(dict(path=name, kind=category, purpose=purpose,
                            origin=REPOSITORY, version=f"git-blob:{git_blob(data)}",
                            sha256=hashlib.sha256(data).hexdigest(), status="awaiting_review",
                            scope="synthetic_reconstruction"))
    return dict(version=1, checkpoint=commit, review=dict(status="awaiting_review", owner_decision=None),
                artifacts=entries, legacy=[dict(id=key, kind=kind, status=status, note=note,
                                                  version=None, sha256=None, origin="preserved_repository_evidence")
                                            for key, kind, status, note in RECORDS])


def git_blob(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data, usedforsecurity=False).hexdigest()


def package_bytes(package):
    return (json.dumps(package, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()


def validate_decisions(package, body, decisions):
    keys = {row["path"]: row["sha256"] for row in package["artifacts"]}
    if (set(decisions) != {"version", "package_sha256", "review", "decisions"} or decisions["version"] != 1
            or decisions["package_sha256"] != hashlib.sha256(body).hexdigest()
            or not re.fullmatch(r"https://github\.com/vasu1765/dincharya-ai/pull/[1-9]\d*(?:#[-\w]+)?",
                                decisions["review"])):
        raise ValueError("Review must identify this exact package and link to repository approval")
    seen = set()
    for row in decisions["decisions"]:
        path = row["path"]
        if (set(row) != {"path", "sha256", "status", "reason"} or path not in keys or path in seen
                or row["sha256"] != keys[path]
                or row["status"] not in {"adopted", "replaced", "archived", "excluded", "awaiting_review"}
                or not isinstance(row["reason"], str) or not 1 <= len(row["reason"].strip()) <= 500):
            raise ValueError("Invalid or ambiguous artifact decision")
        seen.add(path)
    if seen != set(keys):
        raise ValueError("Record a decision for each candidate, including any still awaiting review")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--propose-at", metavar="COMMIT")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--verify-decisions", action="store_true")
    options = parser.parse_args()
    try:
        if options.propose_at:
            sys.stdout.buffer.write(package_bytes(propose(options.propose_at)))
        else:
            path = ROOT / "docs/m2b-repository-review.json"
            if path.resolve() != path:
                raise ValueError("Review package must be a repository file")
            body = path.read_bytes()
            package = json.loads(body)
            if package_bytes(propose(package["checkpoint"])) != body:
                raise ValueError("Review package or artifact digest changed")
            if options.verify_decisions:
                record = ROOT / "docs/m2b-owner-decisions.json"
                if record.resolve() != record:
                    raise ValueError("Review decisions must be a repository file")
                validate_decisions(package, body, json.loads(record.read_text()))
            print("PASS repository source package " + hashlib.sha256(body).hexdigest())
    except (ValueError, OSError, KeyError, TypeError):
        raise SystemExit("Source package validation failed; inspect the registered review inputs.") from None


if __name__ == "__main__":
    main()
