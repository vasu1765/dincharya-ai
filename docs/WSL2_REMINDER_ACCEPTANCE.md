# WSL2 reminder acceptance

Run from the PR branch root in an unprivileged WSL2 shell with PostgreSQL 17
server/client binaries and a Python environment with the gateway requirements.
Use only the operator-authorized schema-only baseline at its exact path and a
dedicated BotFather test bot. Run the sections in order. Stop on any mismatch.

## 1. Start and verify a disposable database

Start a clean shell with `env -i HOME="$HOME" PATH="$PATH" TERM="$TERM" bash --noprofile --norc`
from the repository root. Run:

```bash
set -euo pipefail
umask 077
PG_BIN=/usr/lib/postgresql/17/bin
export DINCHARYA_TEST_PG_PORT=55432
read -r -p 'Exact approved schema-only baseline path: ' BASELINE
test -f "$BASELINE" && test ! -L "$BASELINE"
work=$(mktemp -d /tmp/dincharya-acceptance.XXXXXXXX)
cleanup() {
  if [[ -n "${gateway_pid:-}" ]]; then
    kill -INT "$gateway_pid" 2>/dev/null || true
    wait "$gateway_pid" || true
  fi
  if [[ -f "$work/data/postmaster.pid" ]]; then
    "$PG_BIN/pg_ctl" -D "$work/data" -m fast -w stop || return 1
  fi
  rm -rf -- "$work"
}
trap cleanup EXIT
DINCHARYA_TEST_PG_PASSWORD=$(openssl rand -hex 24)
export DINCHARYA_TEST_PG_PASSWORD
printf '%s\n' "$DINCHARYA_TEST_PG_PASSWORD" > "$work/pw"
"$PG_BIN/initdb" -D "$work/data" -U synthetic_test --auth=scram-sha-256 --pwfile="$work/pw"
rm -- "$work/pw"
"$PG_BIN/pg_ctl" -D "$work/data" -l "$work/server.log" -w start \
  -o "-h 127.0.0.1 -p $DINCHARYA_TEST_PG_PORT -k $work"
export TEST_PSQL="$PG_BIN/psql"
db() {
  PGPASSWORD="$DINCHARYA_TEST_PG_PASSWORD" "$TEST_PSQL" -X -v ON_ERROR_STOP=1 \
    -h 127.0.0.1 -p "$DINCHARYA_TEST_PG_PORT" -U synthetic_test "$@"
}
db -d postgres -c 'CREATE DATABASE dincharya_app_test'
q() { db -d dincharya_app_test "$@"; }
test "$(q -Atc 'SHOW data_directory')" = "$work/data"
test "$(q -Atc 'SHOW listen_addresses')" = 127.0.0.1
test "$(q -Atc 'SELECT current_database(), session_user, inet_server_addr(), inet_server_port()')" \
  = "dincharya_app_test|synthetic_test|127.0.0.1|$DINCHARYA_TEST_PG_PORT"
test "$(q -Atc 'SELECT current_setting($$server_version_num$$)::int / 10000')" = 17
test "$(q -Atc "SELECT count(*) FROM pg_tables WHERE schemaname='public'")" = 0
PYTHONPATH=scripts python -B -c 'import pathlib,sys; from source_sync import validate_schema; sys.stdout.buffer.write(validate_schema(pathlib.Path(sys.argv[1]).read_bytes()))' "$BASELINE" | q -q
python -B - <<'PY' | q -q
from database.migrate import render_migrations
from pathlib import Path
print(render_migrations(sorted(Path('database/migrations').glob('[0-9][0-9][0-9][0-9]_*.sql'))))
PY
q -c 'SELECT version FROM public.application_migration_ledger ORDER BY version'
```

This uses a fresh cluster under a private temporary directory, a loopback-only
listener, an invented role credential and no Docker or n8n. Check that only the
two expected migration versions are listed.

## 2. Run focused SQL checks

```bash
q -f tests/sql/reminders.sql
PYTHONPATH=tests/integration python -B - <<'PY'
import os
import subprocess
from application_runner import ApplicationRunner

class LocalRunner(ApplicationRunner):
    def sql(self, statement, database):
        assert database == 'dincharya_app_test'
        return subprocess.check_output([
            os.environ['TEST_PSQL'], '-XAt', '-v', 'ON_ERROR_STOP=1',
            '-h', '127.0.0.1', '-p', os.environ['DINCHARYA_TEST_PG_PORT'],
            '-U', 'synthetic_test', '-d', database, '-c', statement,
        ], env={**os.environ, 'PGPASSWORD': os.environ['DINCHARYA_TEST_PG_PASSWORD']},
            text=True, timeout=30).strip()

LocalRunner.__new__(LocalRunner).concurrent_tests()
PY
```

Expect the SQL script to finish with `ROLLBACK` after the pending-approval and
five-attempt cap assertions. Expect one successful decision, one successful
claim, and a successful acknowledgement in the concurrent check. That check
commits synthetic rows. Reset the disposable database before the bot run by
stopping this shell with `exit`, confirming cleanup, then repeating section 1
in a fresh shell.

## 3. Verify the dedicated bot independently

Identify the test bot's username in BotFather and open that exact bot in
Telegram. Enter its token silently and enter the test owner's numeric ID.
Verify `getMe` matches the BotFather username, then pin the returned ID:

```bash
read -r -s -p 'Dedicated test bot token: ' DINCHARYA_TEST_BOT_TOKEN; printf '\n'
export DINCHARYA_TEST_BOT_TOKEN
read -r -p 'BotFather test bot username (without @): ' test_bot_username
DINCHARYA_TEST_BOT_ID=$(python -B - "$test_bot_username" <<'PY'
import json, os, sys, urllib.request
try:
    token = os.environ['DINCHARYA_TEST_BOT_TOKEN']
    with urllib.request.urlopen(f'https://api.telegram.org/bot{token}/getMe', timeout=10) as response:
        body = json.load(response)
    bot = body['result']
    assert body['ok'] is True and bot['is_bot'] is True
    assert bot['username'].casefold() == sys.argv[1].casefold()
    print(bot['id'])
except Exception:
    raise SystemExit('Test bot identity verification failed') from None
PY
)
test -n "$DINCHARYA_TEST_BOT_ID"
export DINCHARYA_TEST_BOT_ID
read -r -p 'Private test owner numeric ID: ' DINCHARYA_TEST_OWNER_ID
export DINCHARYA_TEST_OWNER_ID
PYTHONPATH=. python -B telegram-gateway/gateway.py --acceptance >"$work/gateway.log" 2>&1 &
gateway_pid=$!
```

Use the private chat and run exactly one gateway poller. Ensure the gateway
stays running before sending commands. Use a unique synthetic title such as
`WSL acceptance 01`.

## 4. Observe approval, contention and acknowledgement

1. Send `/remind YYYY-MM-DD HH:MM WSL acceptance 01` with an Asia/Kolkata
   time several minutes ahead. Record the returned numeric request ID. Run
   `q -c 'SELECT id,status,event_id FROM public.schedule_change_requests ORDER BY id'`
   and `q -c 'SELECT count(*) FROM public.reminder_deliveries'`.
   Expect pending, a null event ID, and zero deliveries.
2. Send `/approve_reminder ID` from the owner chat. Expect “Reminder scheduled.”
   Recheck the request for approved status and a single event ID. Replay the
   command and expect a declined decision.
3. Before the due minute, open a separate PostgreSQL session with `q`. In that
   session run `SELECT pg_advisory_lock(20261112,3);` and leave the session open.
   After the due time, wait at least two 15-second ticks. Expect no Telegram send
   and no claim. Check with
   `q -c 'SELECT count(*) FROM public.reminder_deliveries WHERE attempts > 0'`
   and expect zero. From a separate client to the same verified test database,
   `SELECT pg_try_advisory_lock(20261112,3);` must return false. This probes
   contention without starting a second Telegram poller.
4. In the lock-holding session run `\q` to release the lock by disconnecting.
   Within the next two ticks expect one Telegram reminder. Check
   `q -c 'SELECT event_id,status,attempts,sent_at IS NOT NULL AS acknowledged,worker_token IS NULL AS released FROM public.reminder_deliveries ORDER BY id'`.
   Expect exactly one matching row with `sent`, one attempt, and both flags
   true. Wait two further ticks and verify the row and chat count are unchanged.
   Stop and wait for the gateway as shown below, then run
   `q -Atc 'SELECT pg_try_advisory_lock(20261112,3)'` and expect `t`.
   That one-shot session releases its own lock on exit.

## 5. Clean up and record evidence

```bash
kill -INT "$gateway_pid" 2>/dev/null || true
wait "$gateway_pid" || true
unset gateway_pid
q -Atc 'SELECT pg_try_advisory_lock(20261112,3)'  # Expect t.
unset DINCHARYA_TEST_BOT_TOKEN DINCHARYA_TEST_PG_PASSWORD
exit
```

On an early error, stop the exact test gateway PID before leaving the shell.
The EXIT trap stops the exact temporary cluster and removes its files. Verify
the dedicated port is no longer listening. Revoke the test token in BotFather
if the bot is being retired. Record the PR commit, PostgreSQL major version,
test identity checks, SQL exit results, contention and release results, message
count and ledger status/attempt count. Share only sanitized results. Keep tokens,
chat identifiers, raw logs, schema bytes and private paths out of Git and the PR.

Telegram message-ID persistence is a separate follow-up unless runtime evidence
shows it is needed to correct a failure.
