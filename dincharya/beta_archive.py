"""Encrypt a streamed synthetic dump for a pinned recipient, without network access."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def seal(source, directory, certificate, cert_sha256):
    if not re.fullmatch("[0-9a-f]{64}", cert_sha256):
        raise ValueError("Expected SHA-256 for the reviewed PEM bytes")
    pem = Path(certificate).read_bytes()
    if hashlib.sha256(pem).hexdigest() != cert_sha256:
        raise ValueError("Backup recipient pin mismatch")
    with tempfile.TemporaryDirectory(dir=directory) as temp:
        recipient = Path(temp) / "recipient.pem"
        recipient.write_bytes(pem)
        sealed = Path(temp) / "archive"
        with sealed.open("xb") as output:
            subprocess.run(["openssl", "cms", "-encrypt", "-binary", "-aes-256-gcm",
                            "-outform", "DER", str(recipient)], stdin=source,
                           stdout=output, stderr=subprocess.DEVNULL, check=True)
            output.flush()
            os.fsync(output.fileno())
        with sealed.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        destination = Path(directory) / (digest + ".cms")
        os.chmod(sealed, 0o600)
        os.link(sealed, destination)
        return digest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("certificate", type=Path)
    parser.add_argument("cert_sha256")
    args = parser.parse_args()
    print(json.dumps({"ciphertext_sha256": seal(sys.stdin.buffer, args.directory,
                                                args.certificate, args.cert_sha256)}))
