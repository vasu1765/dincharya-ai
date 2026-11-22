"""Explicitly authorized owner-only private Telegram acceptance, never a general gateway."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time

from m2h_cycle6_baseline import BASELINE, ExactRunner, base, service_main
from dincharya.lunar_runtime import build_service, read_private, validate_test_bot
from dincharya.lunar_service import envelope
from dincharya.private_acceptance import (
    PrivateSession, REMINDER, SILENT, Scope, StopAcceptance, require,
)
from lunar_handlers import OrchestrationClient

DAEMON = "44c1ef83-c50e-4ecc-8f19-4b112bc40f29"
BRANCH = "development/m2h-private-telegram-acceptance"


class AcceptanceLedger:
    def __init__(self, admin, scope):
        self.admin, self.scope = admin, scope
        self.reminder_event_id = None

    def assert_fresh(self):
        for relation in ("public.schedule_events", "public.recurrence_rules", "public.schedule_change_requests",
                         "lunar_private.recurring_control", "lunar_private.occurrences",
                         "public.reminder_deliveries", "lunar_private.notification_slot"):
            require(self.admin.execute(f"SELECT count(*) FROM {relation}").fetchone() == (0,),
                    "Disposable database contains pre-existing work")

    def verify_schedule(self, count):
        db = self.admin
        rows = db.execute(
            "SELECT e.id,e.title,e.start_time,e.timezone,e.enabled,r.frequency,r.start_date,p.offsets "
            "FROM public.schedule_events e LEFT JOIN public.recurrence_rules r ON r.event_id=e.id "
            "LEFT JOIN lunar_private.notification_policy p ON p.event_id=e.id ORDER BY e.id"
        ).fetchall()
        require(len(rows) == count, "Unexpected appointment count")
        plan = ((SILENT, self.scope.at(6), []), (REMINDER, self.scope.at(8), [0]))
        for row, (title, at, offsets) in zip(rows, plan):
            require(row[1:] == (title, at.time(), "Asia/Kolkata", True, "once", at.date(), offsets),
                    "Stored appointment differs from the approved scope")
        require(db.execute("SELECT count(*) FROM lunar_private.occurrences").fetchone() == (0,),
                "Unexpected lunar projection")
        if count == 2:
            self.reminder_event_id = rows[1][0]

    def verify_delivery(self, message=None):
        db = self.admin
        require(db.execute("SELECT count(*) FROM public.reminder_deliveries").fetchone() == (0,),
                "Unexpected legacy reminder work")
        rows = db.execute(
            "SELECT event_id,occurrence_date,offset_minutes,due_at,status,attempts,telegram_chat_id,telegram_message_id "
            "FROM lunar_private.notification_slot"
        ).fetchall()
        expected = (self.reminder_event_id, self.scope.at(8).date(), 0, self.scope.at(8))
        tail = ("sent", 1, self.scope.owner_id, message) if message is not None else ("pending", 0, None, None)
        require(rows == [expected + tail], "Silent or reminder ledger differs from the approved scope")


class BotAPI:
    def __init__(self, client, credential):
        self.client = client
        self.url = "https://api.telegram.org/bot" + credential + "/"

    def __call__(self, method, payload):
        require(method in {"getMe", "getChat", "getWebhookInfo", "getUpdates", "answerCallbackQuery", "sendMessage"},
                "Unexpected Telegram operation")
        try:
            response = self.client.post(self.url + method, json=payload)
            value = response.json()
        except Exception:
            raise StopAcceptance("Telegram response unavailable. Stop without retry") from None
        require(response.status_code == 200 and isinstance(value, dict)
                and value.get("ok") is True and "result" in value,
                "Telegram rejected or could not confirm the operation. Stop without retry")
        return value["result"]


class PrivateRunner(ExactRunner):
    label = "Bounded private Telegram"
    migrations = (*ExactRunner.migrations, "0014_synthetic_restore_fence.sql", "0015_managed_receipt_safety.sql")
    server_script = Path(__file__).name

    def configure_service(self):
        super().configure_service()
        self.config["development_restore_fence"] = True

    async def journey(self):
        import httpx
        import psycopg

        self.checkpoint("Isolated relay and disposable database")
        service = build_service(self.config)
        pg_socket = self.config["connections"]["owner"]["host"]
        auth = {}
        auth["password"] = self.env["DINCHARYA_TEST_DB_PASSWORD"]
        endpoint = "http://n8n/webhook/m2g-lunar"
        with (
            psycopg.connect(host=pg_socket, dbname="dincharya_app_test", user="synthetic_test",
                            autocommit=True, passfile="/dev/null", **auth) as admin,
            httpx.Client(transport=httpx.HTTPTransport(uds=self.n8n_socket), trust_env=False, timeout=8) as relay,
            httpx.Client(trust_env=False, timeout=5, follow_redirects=False) as wire,
        ):
            require(abs(admin.execute("SELECT clock_timestamp()").fetchone()[0] - now()) < timedelta(seconds=2),
                    "Disposable database clock differs from the runner")
            value, signature = envelope(service.command_key, {"operation": "recurring_rules"}, "private-preflight")
            headers = {"x-dincharya-signature": signature}
            answer = relay.post(endpoint, json=value, headers=headers)
            require(answer.status_code == 200 and answer.json().get("status") == "listed",
                    "Signed isolated relay unavailable")
            denied = relay.post(endpoint, json=value, headers={"x-dincharya-signature": "0" * 64})
            require(denied.status_code == 200 and denied.json() == {"status": "denied"},
                    "Isolated relay accepted an invalid signature")
            session = PrivateSession(
                self.scope, BotAPI(wire, self.telegram["token"]),
                OrchestrationClient(relay, endpoint, service.command_key),
                AcceptanceLedger(admin, self.scope), service.run_development_slots, now, time.sleep,
            )
            self.checkpoint("Owner-only workflow and capped delivery")
            try:
                session.run()
            finally:
                print(f"SUMMARY chat_attempts={session.attempts} chat_acknowledgements={len(session.receipts)} "
                      f"reminder_attempts={session.reminder_attempts} "
                      f"telegram_reminder_acknowledged={session.reminder_receipt is not None}", flush=True)
        require(self.baseline.read_bytes() == self.original, "Authorized schema input changed")
        print("PASS five workflow messages, one reminder, one paired receipt, zero silent sends and no duplicates",
              flush=True)


def now():
    return datetime.now(timezone.utc)


def checkout_revision(root):
    def git(*args):
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        return subprocess.check_output(["git", *args], cwd=root, env=env,
                                       stderr=subprocess.DEVNULL, text=True).strip()
    require(git("branch", "--show-current") == BRANCH and not git("status", "--porcelain", "--untracked-files=all"),
            "Expected a clean checkout on the private acceptance branch")
    return git("rev-parse", "HEAD")


@contextmanager
def reserve_run(approval_path, scope):
    """A process lock plus durable one-use window reservation before any network I/O."""
    directory = approval_path.parent
    info = directory.stat()
    require(directory == directory.resolve() and info.st_uid == os.geteuid() and info.st_mode & 0o077 == 0,
            "Approval directory must be private")
    lock_path = Path("/tmp") / f"dincharya-private-acceptance-{os.geteuid()}.lock"
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        lock = os.fstat(fd)
        require(stat.S_ISREG(lock.st_mode) and lock.st_uid == os.geteuid() and lock.st_nlink == 1
                and lock.st_mode & 0o077 == 0, "Acceptance supervisor lock is unsafe")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Global per-user path binds the bot/recipient/window regardless of which
        # approval file or directory was supplied. The digest contains no token.
        key = hashlib.sha256(f"{scope.bot_id}|{scope.owner_id}|{scope.start.isoformat()}".encode()).hexdigest()
        issued = lock_path.with_name(lock_path.name + "." + key)
        marker = os.open(issued, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            os.fsync(marker)
        finally:
            os.close(marker)
        yield
    finally:
        os.close(fd)


def main():
    if not sys.argv[1:]:
        service_main()
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval-file", required=True, type=Path)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--expected-daemon-id", required=True)
    parser.add_argument("--ephemeris", required=True, type=Path)
    parser.add_argument("--execute-approved", action="store_true")
    parser.add_argument("--live-approved", action="store_true")
    args = parser.parse_args()
    require(__debug__ and args.execute_approved and args.live_approved and args.expected_daemon_id == DAEMON,
            "Explicit approval flags and the verified daemon are required")
    require(not any(key.startswith("PG") or key.lower() in {"http_proxy", "https_proxy", "all_proxy", "ssl_cert_file",
                                                           "ssl_cert_dir"} for key in os.environ),
            "Clear inherited database, proxy and certificate settings")
    revision = checkout_revision(base.ROOT)
    require(revision == args.expected_revision, "Checked-out revision differs from the approval")
    require(BASELINE.is_file() and BASELINE.resolve() == BASELINE, "Exact authorized schema unavailable")
    info = read_private(args.approval_file)
    require(isinstance(info, dict) and set(info) == {"approval", "telegram"}, "Unexpected private configuration")
    scope = Scope.from_approval(info["approval"], revision, now())
    validate_test_bot(info["telegram"], scope.owner_id)
    require(info["telegram"]["bot_id"] == scope.bot_id, "Bot credential differs from the approval")
    PrivateRunner.baseline = BASELINE
    PrivateRunner.kernel = str(args.ephemeris.resolve(strict=True))
    PrivateRunner.owner_id = scope.owner_id
    PrivateRunner.scope = scope
    PrivateRunner.telegram = info["telegram"]
    base.Runner = PrivateRunner

    def interrupt(signum, frame):
        raise StopAcceptance("Interrupted. Stop without retry and remove the disposable session")

    signal.signal(signal.SIGTERM, interrupt)
    with reserve_run(args.approval_file.absolute(), scope):
        base.execute(DAEMON)


if __name__ == "__main__":
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        print(str(error) if isinstance(error, StopAcceptance) else
              "Private acceptance stopped. Inspect fixed stage headings. No restart or resend.",
              file=sys.stderr)
        raise SystemExit(1) from None
