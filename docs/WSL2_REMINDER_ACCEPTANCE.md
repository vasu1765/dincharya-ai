# WSL Codex task for PR #1

Use a clean checkout of the PR branch and record its commit. Run the focused SQL
and Telegram acceptance below, then post sanitized evidence directly to
[PR #1](https://github.com/vasu1765/dincharya-ai/pull/1). Use the local Docker
Desktop daemon and the same pinned PostgreSQL 17 image as the passing integration.
This PostgreSQL-only path leaves the existing integration project alone and
avoids a host PostgreSQL install or an n8n startup.

Use the exact approved schema-only baseline and previously verified local daemon
ID. Reuse an existing Python environment if it can import `psycopg`, `telegram`,
`httpx`, `dotenv` and create the Telegram job queue. If needed, provision a
temporary venv with the repository gateway requirements using already available
package access. Check these prerequisites locally first. Ask the owner only for
missing operator-held inputs or the explicit Telegram approval. Do not read
production environment files or use production bot credentials.

## 1. Start and verify a disposable database

From the branch root, use a clean Bash shell with the selected Python on PATH.
Use `env -i HOME="$HOME" PATH="$PATH" TERM="$TERM" bash --noprofile --norc`.
Run:

```bash
set -euo pipefail
umask 077
read -r -p 'Previously verified local Docker daemon ID: ' expected_daemon
read -r -p 'Exact approved schema-only baseline path: ' BASELINE
test -f "$BASELINE" && test ! -L "$BASELINE"
work=$(mktemp -d /tmp/dincharya-acceptance.XXXXXXXX)
export TEST_DOCKER_CONFIG="$work/docker"
mkdir "$TEST_DOCKER_CONFIG"
export TEST_CONTAINER="${work##*/}"
export DINCHARYA_TEST_PG_PORT=55432
d() { docker --config "$TEST_DOCKER_CONFIG" --host unix:///var/run/docker.sock "$@"; }
cleanup() {
  if [[ -n "${gateway_pid:-}" ]]; then
    kill -TERM "$gateway_pid" 2>/dev/null || true
    wait "$gateway_pid" || true
  fi
  if [[ -n "${container_id:-}" ]]; then
    d rm -f -v "$container_id" >/dev/null || return 1
  fi
  rm -rf -- "$work"
}
trap cleanup EXIT
test -n "$expected_daemon"
test "$(d info --format '{{.ID}}|{{.OperatingSystem}}|{{.Name}}|{{.OSType}}')" \
  = "$expected_daemon|Docker Desktop|docker-desktop|linux"
image=$(PYTHONPATH=tests/integration python -B -c 'from runner import IMAGES; print(IMAGES["postgres-test"])')
test "$(d image inspect --format '{{.Id}}' "$image")" = "$image"
DINCHARYA_TEST_PG_PASSWORD=$(openssl rand -hex 24)
export DINCHARYA_TEST_PG_PASSWORD
printf -v POSTGRES_PASSWORD %s "$DINCHARYA_TEST_PG_PASSWORD"
export POSTGRES_PASSWORD
container_id=$(d run -d --pull=never --name "$TEST_CONTAINER" --read-only \
  --security-opt no-new-privileges --memory 512m \
  --tmpfs /var/lib/postgresql/data:size=256m --tmpfs /var/run/postgresql:size=16m \
  --tmpfs /tmp:size=32m -p "127.0.0.1:$DINCHARYA_TEST_PG_PORT:5432" \
  -e POSTGRES_PASSWORD -e POSTGRES_USER=synthetic_test -e POSTGRES_DB=dincharya_app_test "$image")
unset POSTGRES_PASSWORD
test "$(d inspect --format '{{.Image}}' "$container_id")" = "$image"
test "$(d port "$container_id" 5432/tcp)" = "127.0.0.1:$DINCHARYA_TEST_PG_PORT"
test -z "$(d inspect --format '{{range .Mounts}}{{if ne .Type "tmpfs"}}{{.Type}}{{end}}{{end}}' "$container_id")"
q() {
  local flags=-i
  if [[ "${1:-}" == -it ]]; then flags=-it; shift; fi
  d exec "$flags" "$container_id" psql -X -v ON_ERROR_STOP=1 -U synthetic_test -d dincharya_app_test "$@"
}
for attempt in {1..30}; do
  if d exec "$container_id" pg_isready -h 127.0.0.1 -U synthetic_test -d dincharya_app_test >/dev/null; then break; fi
  sleep 1
done
test "$(q -Atc 'SELECT current_database(), session_user, current_setting($$server_version_num$$)::int / 10000')" = 'dincharya_app_test|synthetic_test|17'
test "$(q -Atc "SELECT count(*) FROM pg_tables WHERE schemaname='public'")" = 0
PYTHONPATH=scripts python -B -c 'import pathlib,sys; from source_sync import validate_schema; sys.stdout.buffer.write(validate_schema(pathlib.Path(sys.argv[1]).read_bytes()))' "$BASELINE" | q -q
python -B - <<'PY' | q -q
from database.migrate import render_migrations
from pathlib import Path
root = Path('database/migrations')
print(render_migrations([root / '0001_gregorian_occurrences.sql',
                         root / '0002_occurrence_reminders.sql']))
PY
q -c 'SELECT version FROM public.application_migration_ledger ORDER BY version'
python -B - <<'PY'
import os
import psycopg
from telegram.ext import Application
import httpx
import dotenv

assert Application.builder().token('101:synthetic').build().job_queue is not None
credentials = {}
credentials['password'] = os.environ['DINCHARYA_TEST_PG_PASSWORD']
with psycopg.connect(hostaddr='127.0.0.1', port=os.environ['DINCHARYA_TEST_PG_PORT'],
                     dbname='dincharya_app_test', user='synthetic_test',
                     passfile='/dev/null', sslmode='disable', connect_timeout=5,
                     **credentials) as conn:
    assert conn.execute('SELECT count(*) FROM public.application_migration_ledger').fetchone() == (2,)
PY
```

Confirm exactly the two expected ledger entries. Keep other delivery workers off.
If the port is occupied, choose an unused loopback port other than 5432 and
use it consistently. If the Docker-published loopback endpoint is unreachable
from WSL, report that preflight blocker. Do not widen the binding.

## 2. Run focused SQL checks

```bash
q < tests/sql/reminders.sql
PYTHONPATH=tests/integration python -B - <<'PY'
import os
import subprocess
from application_runner import ApplicationRunner

class LocalRunner(ApplicationRunner):
    def sql(self, statement, database):
        assert database == 'dincharya_app_test'
        return subprocess.check_output([
            'docker', '--config', os.environ['TEST_DOCKER_CONFIG'],
            '--host', 'unix:///var/run/docker.sock', 'exec', os.environ['TEST_CONTAINER'],
            'psql', '-XAt', '-v', 'ON_ERROR_STOP=1',
            '-U', 'synthetic_test', '-d', database, '-c', statement,
        ],
            text=True, timeout=30).strip()

LocalRunner.__new__(LocalRunner).concurrent_tests()
PY
```

Expect the SQL script to finish with `ROLLBACK` after the pending-approval and
five-attempt cap assertions. Expect one successful decision, one successful
claim, and a successful acknowledgement in the concurrent check. That check
commits synthetic rows. Reset the disposable database before the bot run by exiting this shell, confirming cleanup, and repeating section 1.

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

Use the private chat and run exactly one gateway poller. The owner sends the approval directly in Telegram. Ensure the gateway
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
3. Before the due minute, print the verified disposable container name with
   `printf '%s\n' "$TEST_DOCKER_CONFIG" "$TEST_CONTAINER"`. In a second clean WSL terminal, open a
   lock-holding session with
   `docker --config TEMP_DOCKER_CONFIG --host unix:///var/run/docker.sock exec -it CONTAINER_NAME psql -X -U synthetic_test -d dincharya_app_test`
   using those exact values. In that session run `SELECT pg_advisory_lock(20261112,3);` and leave the session open.
   After the due time, wait at least two 15-second ticks. Expect no Telegram send
   and no claim. Check with
   `q -c 'SELECT count(*) FROM public.reminder_deliveries WHERE attempts > 0'`
   and expect zero. From the original shell,
   `q -Atc 'SELECT pg_try_advisory_lock(20261112,3)'` must return `f`. This probes
   contention without starting a second Telegram poller.
4. In the lock-holding session run `\q` to release the lock by disconnecting.
   Within the next two ticks expect one Telegram reminder. Check
   `q -c 'SELECT event_id,status,attempts,sent_at IS NOT NULL AS acknowledged,worker_token IS NULL AS released FROM public.reminder_deliveries ORDER BY id'`.
   Expect exactly one matching row with `sent`, one attempt, and both flags
   true. Wait two further ticks and verify the row and chat count are unchanged.
   Stop and wait for the gateway as shown below, and verify that its lock can be reacquired. The one-shot client below releases its own lock on exit.

## 5. Clean up and record evidence

```bash
kill -TERM "$gateway_pid" 2>/dev/null || true
wait "$gateway_pid" || true
unset gateway_pid
q -Atc 'SELECT pg_try_advisory_lock(20261112,3)'  # Expect t.
unset DINCHARYA_TEST_BOT_TOKEN DINCHARYA_TEST_PG_PASSWORD
exit
```

On an early error, stop the exact test gateway PID before leaving the shell.
The EXIT trap stops the exact disposable container and its temporary files. From the parent WSL shell, verify the dedicated port is no longer listening
with `ss -H -ltn 'sport = :55432'` (substitute the chosen port). Revoke the test token in BotFather
if the bot is being retired. Record the PR commit, PostgreSQL major version,
test identity checks, SQL exit results, contention and release results, message
count and ledger status/attempt count. Share only sanitized results. Keep tokens,
chat identifiers, raw logs, schema bytes and private paths out of Git and the PR.

Post the sanitized result directly to PR #1 as a comment from WSL Codex. Include the tested commit, each checklist item as pass/fail/blocked, cleanup, and the exact missing prerequisite or safe error category if blocked. Keep the PR draft. Telegram message-ID persistence is a separate follow-up unless runtime evidence shows it is needed to correct a failure.
