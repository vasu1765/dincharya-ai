"""Fixed Linux/amd64 attended image set. The astronomy overlay is child-only."""
import base64
import hashlib
from importlib import metadata
from pathlib import Path
import ssl
import subprocess
import sys

PG = "sha256:ff87138949ad9a46f32ff23bd6852b52ce024a13dffe9b4087be98292cdd3b4f"
APP = "sha256:fff0b1b58321339ad0de04804548cb8ff14c9a929e6eead08ce3cd96535493ca"
N8N = "sha256:6723b440354bb8e1395a1ecee12685fe03923f897bf6e4d5bb2c6c2bd2051697"
WHEEL = "certifi-2025.10.5-py3-none-any.whl"
WHEEL_SHA = "0f212c2744a9bb6de0c56639a6f68afe01ecd92d91f14ae897c4fe7bbeeef0de"
KERNEL_SHA = "c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2"


def verify_images(pg, app, n8n):
    if (pg, app, n8n) != (PG, APP, N8N):
        raise ValueError("Unreviewed image set")


def telegram_tls():
    """Load only the certifi PEM authenticated by the immutable app image's RECORD."""
    dist = metadata.distribution("certifi")
    if dist.version != "2026.10.23":
        raise ValueError("Unexpected Telegram trust distribution")
    entry, = [f for f in dist.files or () if str(f) == "certifi/cacert.pem"]
    data = entry.locate().read_bytes()
    checksum = hashlib.sha256(data).digest()
    if (entry.hash is None or entry.hash.mode != "sha256" or
            entry.hash.value != base64.urlsafe_b64encode(checksum).decode().rstrip("=")):
        raise ValueError("Unexpected Telegram trust bytes")
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_verify_locations(cadata=data.decode("ascii"))
    return ctx, checksum.hex()


def verify_wheel(wheel):
    if wheel.name != WHEEL or hashlib.sha256(wheel.read_bytes()).hexdigest() != WHEEL_SHA:
        raise ValueError("Unexpected astronomy overlay")


def isolated_lookup(question, kernel, wheel):
    verify_wheel(wheel)
    worker = Path(__file__).with_name("attended_astronomy.py").resolve()
    result = subprocess.run([sys.executable, "-I", "-S", "-B", str(worker), str(wheel), str(kernel)],
                            input=question, text=True, capture_output=True, env={"TZ":"UTC"},
                            cwd="/", timeout=30, check=False, close_fds=True)
    if result.returncode or not 0 < len(result.stdout) <= 4096:
        raise RuntimeError("Historical calculation unavailable")
    return result.stdout
