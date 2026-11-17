"""Cycle 4 native n8n relay with a disposable application and simulated Telegram."""
import argparse
from contextlib import ExitStack, contextmanager
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
from socket import socket
import subprocess
import sys
import time

from m2h_development import ROOT, run
import httpx

from dincharya.lunar_http import request_handler
from dincharya.lunar_runtime import build_service
from dincharya.lunar_service import envelope
from m2h_operations import run_operations

VERSION = "2.47.3"
def loopback_port():
    with socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def service_main(port):
    config = json.loads(sys.stdin.readline())
    service = build_service(config)
    with ThreadingHTTPServer(("127.0.0.1", port), request_handler(service)) as server:
        server.serve_forever()


class Relay:
    def __init__(self, work, config, executable, stack):
        self.config = config
        self.work = work
        self.app_port = loopback_port()
        self.n8n_port = loopback_port()
        while self.n8n_port == self.app_port:
            self.n8n_port = loopback_port()
        self.origin = f"http://127.0.0.1:{self.n8n_port}"
        self.url = self.origin + "/webhook/m2g-lunar"
        self.client = stack.enter_context(httpx.Client(trust_env=False, timeout=50))
        self.app = None
        self.restart_service()
        stack.callback(self.stop_service)
        self.environment = {key: os.environ[key] for key in ("PATH", "LANG") if key in os.environ}
        self.environment.update(
            HOME=str(work), N8N_USER_FOLDER=str(work), N8N_HOST="127.0.0.1",
            N8N_LISTEN_ADDRESS="127.0.0.1", N8N_PORT=str(self.n8n_port), N8N_PROTOCOL="http",
            N8N_SECURE_COOKIE="false", N8N_DIAGNOSTICS_ENABLED="false",
            N8N_VERSION_NOTIFICATIONS_ENABLED="false", N8N_TEMPLATES_ENABLED="false",
            N8N_PERSONALIZATION_ENABLED="false", N8N_RUNNERS_ENABLED="false", N8N_LOG_LEVEL="error",
            EXECUTIONS_DATA_SAVE_ON_ERROR="none", EXECUTIONS_DATA_SAVE_ON_SUCCESS="none",
            EXECUTIONS_DATA_SAVE_MANUAL_EXECUTIONS="false", N8N_BLOCK_ENV_ACCESS_IN_NODE="true",
            N8N_ENCRYPTION_KEY=secrets.token_hex(32),
        )
        self.executable = executable
        version = subprocess.check_output([executable, "--version"], env=self.environment,
                                          cwd=work, stderr=subprocess.DEVNULL, timeout=40, text=True).strip()
        if version != VERSION:
            raise ValueError("Reviewed n8n version required")
        self.n8n_log = stack.enter_context((work / "n8n.log").open("wb"))
        self.n8n = self.start_n8n()
        stack.callback(lambda: self.stop(self.n8n))
        self.install_workflow()

    def start_n8n(self):
        child = subprocess.Popen([self.executable, "start"], cwd=self.work, env=self.environment,
                                 stdout=self.n8n_log, stderr=subprocess.STDOUT)
        try:
            self.wait_ready(child, self.origin + "/healthz/readiness")
            return child
        except BaseException:
            self.stop(child)
            raise

    def install_workflow(self):
        flow = json.loads((ROOT / "workflows/m2g-lunar-acceptance.json").read_text())
        assert not flow["active"] and [node["type"] for node in flow["nodes"]] == [
            "n8n-nodes-base.webhook", "n8n-nodes-base.httpRequest"]
        flow["nodes"][1]["parameters"]["url"] = f"http://127.0.0.1:{self.app_port}/lunar"
        if self.config.get("development_historical") is True:
            flow["nodes"][1]["parameters"]["options"]["timeout"] = 40000
        # The relay should expose only the service's structured denial response.
        flow["nodes"][1]["parameters"]["options"]["response"] = {
            "response": {"neverError": True, "responseFormat": "json"},
        }
        identity = dict(email="synthetic@example.invalid", firstName="Synthetic", lastName="Fixture")
        identity["password"] = "X9" + secrets.token_urlsafe(24)
        response = self.client.post(self.origin + "/rest/owner/setup", json=identity)
        response.raise_for_status()
        saved = self.client.post(self.origin + "/rest/workflows", json=flow)
        saved.raise_for_status()
        record = saved.json()["data"]
        activated = self.client.post(self.origin + f"/rest/workflows/{record['id']}/activate",
                                     json={"versionId": record["versionId"]})
        activated.raise_for_status()
        self.wait_webhook()

    @staticmethod
    def stop(child):
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)

    def stop_service(self):
        self.stop(self.app)
        self.app = None

    def wait_ready(self, child, endpoint):
        for _ in range(150):
            if child.poll() is not None:
                raise RuntimeError("Disposable service exited during startup")
            try:
                reply = self.client.get(endpoint, timeout=1)
                if reply.status_code in (200, 501):
                    return
            except httpx.HTTPError:
                pass
            time.sleep(.2)
        raise RuntimeError("Disposable service readiness timed out")

    def restart_service(self):
        self.stop_service()
        self.app = subprocess.Popen([sys.executable, "-B", __file__, "--service-port", str(self.app_port)],
                                    stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, text=True, cwd=ROOT)
        try:
            with self.app.stdin as pipe:
                pipe.write(json.dumps(self.config))
            self.wait_ready(self.app, f"http://127.0.0.1:{self.app_port}/lunar")
        except BaseException:
            self.stop_service()
            raise
        return build_service(self.config)

    def forward(self, value, signature):
        response = self.client.post(self.url, json=value, headers={"x-dincharya-signature": signature})
        response.raise_for_status()
        return response.json()

    def wait_webhook(self):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            value, signature = envelope(self.config["command_key"],
                                        {"operation": "list_lunar_annual", "after": None}, "readiness")
            try:
                response = self.client.post(self.url, json=value, headers={"x-dincharya-signature": signature}, timeout=2)
                if response.status_code == 200 and response.json().get("status") == "listed":
                    return
            except (httpx.HTTPError, ValueError):
                pass
            time.sleep(.2)
        raise RuntimeError("n8n did not register the signed relay webhook")

    def check_signatures(self):
        value, signature = envelope(self.config["command_key"], {"operation": "list_lunar_annual", "after": None}, "signed")
        assert self.forward(value, "0" * 64) == {"status": "denied"}
        assert self.forward(value, signature)["status"] == "listed"
        options = {"operation": "list_lunar_annual", "after": None}
        _, wrong_key = envelope(self.config["tick_key"], options, "signed",
                                clock=lambda: value["timestamp"])
        assert self.forward(value, wrong_key) == {"status": "denied"}
        stale, stale_signature = envelope(self.config["command_key"], options, "stale",
                                          clock=lambda: value["timestamp"] - 120)
        assert self.forward(stale, stale_signature) == {"status": "denied"}
        self.stop_service()
        outage = self.client.post(self.url, json=value, headers={"x-dincharya-signature": signature})
        assert outage.status_code >= 400 or outage.json().get("status") != "listed"
        self.restart_service()
        self.stop(self.n8n)
        self.n8n = self.start_n8n()
        self.wait_webhook()
        value, signature = envelope(self.config["command_key"], options, "after-restart")
        assert self.forward(value, signature)["status"] == "listed"
        print("PASS native n8n signature forwarding, outage and workflow persistence after restart")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin")
    parser.add_argument("--pg-share")
    parser.add_argument("--ephemeris")
    parser.add_argument("--n8n")
    parser.add_argument("--year", type=int)
    parser.add_argument("--service-port", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.service_port is not None:
        service_main(args.service_port)
        return
    if not all((args.pg_bin, args.ephemeris, args.n8n)):
        parser.error("Supply PostgreSQL binaries, public ephemeris and n8n")
    @contextmanager
    def session(work, config):
        with ExitStack() as stack:
            yield Relay(work, config, str(Path(args.n8n).absolute()), stack)

    print("Schema: repository synthetic fixture")
    run(args.pg_bin, args.ephemeris, args.pg_share, args.year, session=session, operations=run_operations)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError, httpx.HTTPError):
        raise SystemExit("Cycle 4 acceptance failed; private input and runtime details suppressed.") from None
