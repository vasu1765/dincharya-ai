"""Native n8n rehearsal inside an isolated disposable application container."""
from datetime import date, timedelta
from http.server import ThreadingHTTPServer
import os
import secrets
import sys
import threading
from uuid import uuid4

import httpx
import json
from pathlib import Path
import time

from dincharya.beta_dispatch import BetaDispatcher
from dincharya.lunar_service import envelope


class DenialMismatch(ValueError):
    pass


def decode(response, *, denial=False):
    if denial and response.status_code in (200, 403):
        if response.json() != {"status": "denied"}:
            raise DenialMismatch()
        return {"status": "denied"}
    response.raise_for_status()
    if denial:
        raise DenialMismatch()
    return response.json()


def install(mark):
    mark("n8n_workflow_read")
    flow = json.loads((Path(__file__).resolve().parents[2] / "workflows/m2g-lunar-acceptance.json").read_bytes())
    if flow["active"] is not False or [n["type"] for n in flow["nodes"]] != [
            "n8n-nodes-base.webhook", "n8n-nodes-base.httpRequest"]:
        raise ValueError("Unexpected workflow")
    params = flow["nodes"][1]["parameters"]
    params["url"] = "http://app:8080/lunar"
    params["options"] = {"timeout": 40000, "response": {"response": {"neverError": True, "responseFormat": "json"}}}
    with httpx.Client(base_url="http://relay:5678", trust_env=False, timeout=10) as client:
        mark("n8n_health")
        for attempt in range(60):
            try:
                client.get("/healthz/readiness").raise_for_status()
                break
            except httpx.HTTPError:
                if attempt == 59:
                    raise
                time.sleep(1)
        mark("n8n_owner_setup")
        client.post("/rest/owner/setup", json=dict(email="fixture@example.invalid", firstName="Test",
                    lastName="Owner", password="X9"+secrets.token_urlsafe(30))).raise_for_status()
        mark("n8n_workflow_create")
        response = client.post("/rest/workflows", json=flow)
        response.raise_for_status()
        record = response.json()["data"]
        mark("n8n_workflow_activate")
        client.post("/rest/workflows/"+record["id"]+"/activate",
                    json={"versionId": record["versionId"]}).raise_for_status()



def connect():
    import psycopg
    return psycopg.connect(host="db", dbname="dincharya_beta_rehearsal", user="beta_gateway",
                           password=os.environ["BETA_GATEWAY_PASSWORD"], connect_timeout=4)


def journey(mark):
    from dincharya.lunar_http import request_handler
    key = secrets.token_hex(32)
    service = BetaDispatcher(connect, key)
    with ThreadingHTTPServer(("0.0.0.0", 8080), request_handler(service)) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            install(mark)
            with httpx.Client(trust_env=False, timeout=15) as client:
                def send(step, update, *, forged=False, denial=False):
                    mark(step)
                    value, signature = envelope(key, {"operation": "beta_update", "update": update}, uuid4().hex)
                    response = client.post("http://relay:5678/webhook/m2g-lunar", json=value,
                                           headers={"x-dincharya-signature": "wrong" if forged else signature})
                    return decode(response, denial=denial)

                owner = {"id": 101, "is_bot": False}
                chat = {"id": 101, "type": "private"}
                msg = {"from": owner, "chat": chat,
                       "text": f"Schedule Synthetic on {date.today()+timedelta(days=2)} at 10:00; at start"}
                update = {"update_id": 1, "message": msg}
                assert send("relay_forged_denial", update, forged=True, denial=True)["status"] == "denied"
                assert send("relay_foreign_owner_denial", {**update, "message": {**msg, "from": {**owner, "id": 102}}}, denial=True)["status"] == "denied"
                token = send("relay_draft", update)["token"]
                assert send("relay_draft_replay", update)["token"] == token
                callback = {"update_id": 2, "callback_query": {"message": {"chat": chat}, "from": owner,
                                                                "data": "confirm/"+token}}
                assert send("relay_confirm", callback)["status"] == "active"
                assert send("relay_confirm_replay", callback)["status"] == "active"
                for number, (op, expected) in enumerate([("pause", "paused"), ("resume", "active"), ("cancel", "cancelled")], start=3):
                    change_msg = {"update_id": number, "message": {**msg, "text": f"/{op} {token}"}}
                    change = send(op+"_preview", change_msg)["token"]
                    assert send(op+"_preview_replay", change_msg)["token"] == change
                    callback["callback_query"]["data"] = "apply/" + str(change)
                    assert send(op+"_apply", callback)["status"] == expected
                    assert send(op+"_apply_replay", callback)["status"] == expected
        finally:
            server.shutdown()
    print("PASS signed relay, private owner, approval replay, pause/resume/cancel")


def run(journey_fn=journey):
    step = "relay_server_start"
    def mark(name):
        nonlocal step
        step = name
    try:
        journey_fn(mark)
    except Exception as exc:
        kind = next((cls.__name__ for cls in (httpx.HTTPStatusError, httpx.RequestError, DenialMismatch,
                    AssertionError, KeyError, ValueError) if isinstance(exc, cls)), "Exception")
        code = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else 0
        print(f"RELAY_FAIL step={step} class={kind} http={code}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    if not __debug__:
        sys.exit("Assertions required")
    sys.exit(run())
