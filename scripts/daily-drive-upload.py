"""Upload one CMS AES-GCM archive to an explicitly pinned Google Drive folder."""
import argparse
import configparser
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

REMOTE = "dincharya-drive"
# id-ct-authEnvelopedData as emitted by openssl cms -encrypt -aes-256-gcm.
CMS_OID = bytes.fromhex("060b2a864886f70d0109100117")


def private_file(path):
    handle = os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb")
    info = os.fstat(handle.fileno())
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600:
        handle.close()
        raise ValueError("Expected a private regular file")
    return handle


def check_remote(config, folder):
    if not re.fullmatch(r"[0-9A-Za-z_-]{10,128}", folder):
        raise ValueError("Expected the approved folder ID")
    values = configparser.ConfigParser(interpolation=None)
    with private_file(config) as handle:
        values.read_string(handle.read(65537).decode())
    if values.defaults() or values.sections() != [REMOTE]:
        raise ValueError("Expected a dedicated remote configuration")
    remote = values[REMOTE]
    if (remote.get("type"), remote.get("scope"), remote.get("root_folder_id")) != ("drive", "drive.file", folder):
        raise ValueError("Drive scope or folder mismatch")
    allowed = {"type", "scope", "root_folder_id", "token", "client_id", "client_secret"}
    if not remote.get("token") or set(remote) - allowed:
        raise ValueError("Expected dedicated owner OAuth")


def check_archive(path):
    with path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
        handle.seek(0)
        prefix = handle.read(24)
    if len(prefix) < 2 or prefix[0] != 0x30:
        raise ValueError("Expected a CMS sequence")
    length = prefix[1]
    start = 2 if length < 128 else 2 + (length & 127)
    if length == 128 or not prefix[start:].startswith(CMS_OID):
        raise ValueError("Expected authenticated enveloped CMS ciphertext")
    subprocess.run(["openssl", "cms", "-cmsout", "-inform", "DER", "-in", str(path),
                    "-outform", "DER", "-out", os.devnull],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=60)
    return digest


def upload(archive, config, folder, rclone):
    check_remote(config, folder)
    if not re.fullmatch(r"[a-f0-9]{64}\.cms", archive.name):
        raise ValueError("Expected a digest-addressed encrypted archive")
    if not rclone.is_absolute() or not rclone.is_file():
        raise ValueError("Use the approved absolute rclone executable")
    env = {k: v for k, v in os.environ.items() if not k.startswith("RCLONE_")}
    remote = f"{REMOTE}:{archive.name}"
    command = [str(rclone), "--config", str(config), "--retries", "1", "--low-level-retries", "1"]
    with tempfile.TemporaryDirectory(dir=archive.parent) as tmp:
        snapshot = Path(tmp) / archive.name
        with private_file(archive) as source, snapshot.open("xb") as target:
            shutil.copyfileobj(source, target)
        digest = check_archive(snapshot)
        if digest != archive.stem:
            raise ValueError("Local ciphertext digest mismatch")
        subprocess.run([*command, "--immutable", "copyto", str(snapshot), remote], env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=900)
        pulled = Path(tmp) / "readback"
        with pulled.open("xb") as handle:
            subprocess.run([*command, "cat", remote, "--count", str(snapshot.stat().st_size + 1)],
                           env=env, stdout=handle, stderr=subprocess.DEVNULL, check=True, timeout=900)
        if check_archive(pulled) != digest:
            raise ValueError("Remote ciphertext digest mismatch")
    return digest


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--folder", required=True)
    parser.add_argument("--rclone", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(upload(args.archive, args.config, args.folder, args.rclone))
    except (OSError, ValueError, configparser.Error, subprocess.SubprocessError) as error:
        print("Drive upload or read-back stopped: "+type(error).__name__, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
