#!/usr/bin/env python3
"""Offline, read-only Git-blob verification of approved *review* inputs.

Never loads credentials, starts services, resolves symlinks, or authorizes a beta.
This validates exact reviewed bytes, NOT runtime safety, adoption or deployment.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

HEX = re.compile(r"[0-9a-f]{40}\\Z")


def git_blob(path):
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\\0" + data).hexdigest()


def verify(root, manifest):
    root = Path(root).resolve(strict=True)
    payload = json.loads(Path(manifest).read_text(encoding="utf-8"))
    if (type(payload) is not dict or payload.get("version") != 1
            or payload.get("scope") != "source-only-development-review"
            or payload.get("launch_authorized") is not False
            or payload.get("telegram_egress_authorized") is not False
            or payload.get("whatsapp_enabled") is not False):
        raise ValueError("Manifest is not an inert source-review inventory")
    entries = payload.get("artifacts")
    if type(entries) is not list or not entries:
        raise ValueError("Empty or malformed artifact inventory")
    seen = set()
    for entry in entries:
        if type(entry) is not dict or set(entry) != {"path", "git_blob"}:
            raise ValueError("Invalid artifact entry")
        relative, expected = entry["path"], entry["git_blob"]
        if type(relative) is not str or type(expected) is not str or not HEX.fullmatch(expected):
            raise ValueError("Invalid artifact path or Git blob")
        posix = PurePosixPath(relative)
        if (posix.is_absolute() or not posix.parts or
                any(part in ("", ".", "..") for part in relative.split("/")) or
                "\\\\" in relative or relative in seen):
            raise ValueError("Unsafe or duplicate source path")
        seen.add(relative)
        current = root
        for part in posix.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError("Symbolic-link source path rejected")
        if not current.is_file():
            raise ValueError("Missing reviewed source: " + relative)
        if git_blob(current) != expected:
            raise ValueError("Source bytes changed: " + relative)
    return len(seen)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--manifest", default="docs/beta-source-pins.json")
    args = parser.parse_args()
    try:
        count = verify(args.root, args.manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("FAIL: source pin verification: " + str(exc), file=sys.stderr)
        return 1
    print(f"PASS: {count} source blobs match review pins; NOT deployment authorization")
    return 0


if __name__ == "__main__":
    sys.exit(main())
