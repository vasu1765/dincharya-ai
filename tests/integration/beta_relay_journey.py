"""Native n8n rehearsal inside an isolated disposable application container."""
from datetime import date, timedelta
from http.server import ThreadingHTTPServer
import os
import secrets
import sys
import threading
from uuid import uuid4

import httpx
import psycopg

from dincharya.beta_dispatch import BetaDispatcher
from dincharya.lunar_http import request_handler
from dincharya.lunar_service import envelope
from staging.laptop.service import install


def connect():
    return psycopg.connect(host="db", dbname="dincharya_beta_rehearsal", user="beta_gateway",
                           password=os.environ["BETA_GATEWAY_PASSWORD"], connect_timeout=4)


def main():
    key = secrets.token_hex(32)
    service = BetaDispatcher(connect, key)
    with ThreadingHTTPServer(("0.0.0.0", 8080), request_handler(service)) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            install()
            with httpx.Client(trust_env=False, timeout=15) as client:
                def send(update, *, forged=False):
                    value, signature = envelope(key, {"operation": "beta_update", "update": update}, uuid4().hex)
                    response = client.post("http://relay:5678/webhook/m2g-lunar", json=value,
                                           headers={"x-dincharya-signature": "wrong" if forged else signature})
                    response.raise_for_status()
                    return response.json()

                owner = {"id": 101, "is_bot": False}
                chat = {"id": 101, "type": "private"}
                msg = {"from": owner, "chat": chat,
                       "text": f"Schedule Synthetic on {date.today()+timedelta(days=2)} at 10:00; at start"}
                update = {"update_id": 1, "message": msg}
                assert send(update, forged=True)["status"] == "denied"
                assert send({**update, "message": {**msg, "from": {**owner, "id": 102}}})["status"] == "denied"
                token = send(update)["token"]
                assert send(update)["token"] == token
                callback = {"update_id": 2, "callback_query": {"message": {"chat": chat}, "from": owner,
                                                                "data": "confirm/"+token}}
                assert send(callback)["status"] == "active"
                assert send(callback)["status"] == "active"
                for number, (op, expected) in enumerate([("pause", "paused"), ("resume", "active"), ("cancel", "cancelled")], start=3):
                    change_msg = {"update_id": number, "message": {**msg, "text": f"/{op} {token}"}}
                    change = send(change_msg)["token"]
                    assert send(change_msg)["token"] == change
                    callback["callback_query"]["data"] = "apply/" + str(change)
                    assert send(callback)["status"] == expected
                    assert send(callback)["status"] == expected
        finally:
            server.shutdown()
    print("PASS signed relay, private owner, approval replay, pause/resume/cancel")


if __name__ == "__main__":
    if not __debug__:
        sys.exit("Assertions required")
    main()
