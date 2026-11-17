"""Restore the isolated Cycle 6 database into independently created roles."""
from datetime import datetime, timezone
import os
from pathlib import Path
import secrets
import subprocess

import psycopg
from psycopg import sql

from dincharya.lunar_runtime import build_service
from dincharya.lunar_service import connection_factory, envelope
from dincharya.reminder_adapters import PostgresReminders
from m2h_operational_acceptance import loopback_port

GROUPS = (
    "dincharya_reconcile_executor", "dincharya_reconcile_operator", "dincharya_worker_executor",
    "dincharya_reminder_worker", "dincharya_lunar_executor", "dincharya_lunar_owner",
    "dincharya_lunar_calculator",
)
BINDINGS = {"owner": "dincharya_lunar_owner", "calculator": "dincharya_lunar_calculator",
            "worker": "dincharya_reminder_worker"}
LEDGERS = (
    ("public.application_migration_ledger", "version"),
    ("public.reminder_deliveries", "id"),
    ("lunar_private.actions", "id"),
    ("lunar_private.calculations", "id"),
    ("lunar_private.recurring_audit", "action"),
    ("lunar_private.notification_slot", "id"),
    ("lunar_private.recurring_health", "owner_subject"),
)


def snapshot(connection):
    return tuple(connection.execute(f"SELECT to_jsonb(t) FROM {table} t ORDER BY {order}").fetchall()
                 for table, order in LEDGERS)


def restore(work, binary, login, roles, admin, *, pg_share, kernel):
    expected = snapshot(admin)
    dump = work / "cross-cluster.dump"

    def command(name, conn, *args):
        return subprocess.run([
            binary / name, "-w", "-h", conn["host"], "-p", str(conn["port"]), "-U", conn["user"], *args,
        ], check=True, env={**os.environ, "PGPASSWORD": conn["password"]}, capture_output=True, timeout=45)

    command("pg_dump", login, "-Fc", "-f", dump, "dincharya_app_test")
    directory = work / "restored-cluster"
    phrase = secrets.token_urlsafe(32)
    pw = work / "restore-bootstrap"
    with open(pw, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as handle:
        handle.write(phrase + "\n")
    subprocess.run([binary / "initdb", "-D", directory, "-U", "synthetic_test", "--auth-host=scram-sha-256",
                    "--no-locale", "-E", "UTF8", "--pwfile", pw,
                    *(["-L", str(Path(pg_share).resolve())] if pg_share else [])],
                   check=True, capture_output=True, timeout=45)
    pw.unlink()
    port = loopback_port()
    pg = [binary / "pg_ctl", "-D", directory]
    config = (f"-c listen_addresses=127.0.0.1 -c unix_socket_directories='' -p {port} "
              "-c log_statement=none -c log_min_error_statement=panic "
              "-c log_parameter_max_length=0 -c log_parameter_max_length_on_error=0")
    subprocess.run([*pg, "-l", work / "restore-postgres.log", "-o", config, "start"],
                   check=True, capture_output=True, timeout=45)
    try:
        target = dict(login, port=port)
        target["password"] = phrase
        recreated = {}
        with psycopg.connect(**target, dbname="postgres", autocommit=True) as conn:
            for group in reversed(GROUPS):
                conn.execute(sql.SQL("CREATE ROLE {} NOLOGIN NOINHERIT").format(sql.Identifier(group)))
            for kind in ("worker", "calculator", "owner"):
                current = roles[kind]
                credential = secrets.token_urlsafe(24)
                account = sql.Identifier(current["user"])
                conn.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(account, sql.Literal(credential)))
                conn.execute(sql.SQL("GRANT {} TO {}").format(sql.Identifier(BINDINGS[kind]), account))
                recreated[kind] = dict(current, port=port)
                recreated[kind]["password"] = credential
            conn.execute("CREATE DATABASE dincharya_app_test")
        command("pg_restore", target, "--exit-on-error", "--single-transaction", "-d", "dincharya_app_test", dump)
        with psycopg.connect(**target, dbname="dincharya_app_test", autocommit=True) as conn:
            assert snapshot(conn) == expected
            # OIDs are cluster-local. Map only known disposable principals by
            # their exact role names and kinds. Immutable audit OIDs are evidence.
            owner, calculator = (recreated[kind]["user"] for kind in ("owner", "calculator"))
            registered = conn.execute(
                "SELECT p.kind,p.role_name,p.role_oid,r.oid,p.owner_subject,p.enabled FROM lunar_private.principals p "
                "JOIN pg_roles r ON r.rolname=p.role_name ORDER BY p.kind"
            ).fetchall()
            assert [(r[0], r[1]) for r in registered] == [("calculator", calculator), ("owner", owner)]
            assert any(row[2] != row[3] for row in registered)
            with conn.transaction():
                conn.execute("DELETE FROM lunar_private.principals WHERE role_name IN (%s,%s)", (owner, calculator))
                for kind, name, _, after, subject, enabled in registered:
                    conn.execute("INSERT INTO lunar_private.principals VALUES(%s,%s,%s,%s,%s)",
                                 (after, name, subject, kind, enabled))
            permit = dict(development_astronomy=True, development_recurring=True, development_historical=True,
                          public_ephemeris=kernel, owner_id=101, connections=recreated,
                          catalog={"synthetic": True, "astronomy_enabled": False, "fixtures": {}},
                          command_key=secrets.token_hex(32), tick_key=secrets.token_hex(32),
                          review_key=secrets.token_hex(32))
            service = build_service(permit)
            value, signature = envelope(service.tick_key, {"operation": "project_tick"}, "restored-projection")
            assert service.handle(value, signature)["status"] == "projected"
            repo = PostgresReminders(connection_factory(recreated["worker"]), notification_slots=True)
            # An ambiguous delivery remains terminal and keeps its history.
            uncertain = {row[0] for row in conn.execute(
                "SELECT id FROM lunar_private.notification_slot WHERE status='uncertain'")}
            assert uncertain
            assert not uncertain.intersection(claim.delivery_id for claim in repo.claim(datetime.now(timezone.utc), 100))
            assert all(conn.execute("SELECT status FROM lunar_private.notification_slot WHERE id=%s",
                                    (ident,)).fetchone() == ("uncertain",) for ident in uncertain)
            after = snapshot(conn)
            assert after[:5] == expected[:5]
            assert after[-1] != expected[-1]  # New projection-health heartbeat only.
    finally:
        subprocess.run([*pg, "-m", "fast", "stop"], check=True, timeout=45, capture_output=True)
    print("PASS cross-cluster restore with independently recreated roles, preserved audit and no uncertain resend")
