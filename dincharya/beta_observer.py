"""Bounded external observation using a pinned SSH alias and a forced status command."""
import argparse
import json
import re
import subprocess
import time


def state(sample, revision):
    if not isinstance(revision, str) or not re.fullmatch("[0-9a-f]{40}", revision):
        raise ValueError("Invalid candidate revision")
    if not isinstance(sample, dict) or sample.get("project") != "dincharya-personal-beta" or sample.get("revision") != revision:
        return "unavailable"
    if sample.get("relay") != "ready" or any(type(sample.get(k)) is not int or sample[k] < 0 for k in ("due", "sending", "uncertain", "dead")):
        return "unavailable"
    if sample["uncertain"] or sample["dead"]:
        return "review_delivery"
    ages = ("heartbeat_age_seconds", "oldest_due_seconds", "oldest_sending_seconds")
    if (sample.get("fenced_single_host") is not True or
            any(type(sample.get(k)) is not int or sample[k] < 0 for k in ages)):
        return "unavailable"
    if sample["heartbeat_age_seconds"] >= 30:
        return "worker_stalled"
    if (sample["oldest_due_seconds"] >= 60 or sample["oldest_sending_seconds"] >= 120
            or sample["sending"] > 1):
        return "backlog"
    return "available"


def observe(alias, revision, samples, *, probe=subprocess.run, emit=print, wait=time.sleep):
    if not re.fullmatch("[A-Za-z0-9][A-Za-z0-9-]{0,60}", alias) or not 1 <= samples <= 480:
        raise ValueError("Invalid monitor arguments")
    state(None, revision)
    previous = None
    for index in range(samples):
        try:
            response = probe(["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                              "-o", "ClearAllForwardings=yes", "-o", "ForwardAgent=no",
                              "-o", "ConnectTimeout=4", alias, "status"],
                             capture_output=True, check=True, timeout=10)
            current = state(json.loads(response.stdout), revision)
        except (ValueError, OSError, subprocess.SubprocessError):
            current = "unavailable"
        emit(json.dumps({"sample": index + 1, "state": current,
                         "simulated_owner_alert": current != previous and
                         (previous is not None or current != "available")}))
        previous = current
        if index + 1 < samples:
            wait(15)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("alias")
    parser.add_argument("revision")
    parser.add_argument("--samples", type=int, required=True)
    args = parser.parse_args()
    observe(args.alias, args.revision, args.samples)
