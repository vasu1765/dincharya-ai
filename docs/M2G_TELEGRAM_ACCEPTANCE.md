# M2G private Telegram acceptance — prepared, NOT authorized/executed

The real SDK/psycopg/n8n/worker path passed isolated testing with Telegram IO
simulated. See [results](M2G_TELEGRAM_RESULTS.md). This runbook is a future
**one-reminder** acceptance using only @dincharya_acceptance_test_bot, one private
owner and a fresh disposable database. It does not authorize live calls itself.
Stop until the owner explicitly approves this exact scope. No production/VPS,
merge, real astronomical prediction, resend/reset or existing service change.

## Prerequisites and configuration

Use development/m2g-telegram-integration and the reviewed checkpoint. Git metadata
may require normal WSL commit/push from HANDOFF. Install the isolated runtime:

```bash
python3 -m venv /tmp/dincharya-m2g-runtime
/tmp/dincharya-m2g-runtime/bin/python -m pip --isolated --no-cache-dir install \
  --index-url https://pypi.org/simple -r telegram-gateway/requirements-m2g.txt
```

The acceptance launcher requires both --execute-approved and --live-approved.
It rejects credentials until these flags are supplied, validates restricted
owner-only file/UID/no-symlink/no-hardlink/outside-Git requirements, bot token/ID
pin and positive owner ID. Network getMe must independently confirm the numeric
bot ID and exact username. The application rejects production DB names, unsafe
loopback defaults, inherited PG settings and privileged application logins.

After approval, enter replacement credentials ONLY in a local WSL terminal:

```bash
private_dir=$(mktemp -d /tmp/dincharya-m2g-credentials-XXXXXX)
chmod 700 "$private_dir"
python3 - "$private_dir/credentials.json" <<'PY'
import getpass,json,os,sys
values={}
values['token']=getpass.getpass('Dedicated test-bot token (hidden): ')
values['owner_id']=int(getpass.getpass('Private test owner ID (hidden): '))
values['bot_id']=int(getpass.getpass('Independently pinned dedicated bot ID (hidden): '))
fd=os.open(sys.argv[1],os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as file:json.dump(values,file)
print('Saved restricted credentials; contents were not printed.')
PY
```

Never paste these values in chat, prompts, argv, shell history, .env or repository
files. No credential file was opened while preparing this checkpoint. This step
must occur only after live approval; do not reuse an exposed/revoked token.

## Prepare the isolated live environment (after approval only)

Terminal1, repository root:

```bash
env -i PATH=/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 PYTHONPATH="$PWD" \
  /tmp/dincharya-m2g-runtime/bin/python -B tests/integration/m2g_live_prepare.py \
  --credentials "$private_dir/credentials.json" \
  --baseline /home/vasu1765/dincharya-backups/baseline-20261112T132918Z-d5V7Hf/application-schema.sql \
  --expected-daemon-id 44c1ef83-c50e-4ecc-8f19-4b112bc40f29 \
  --execute-approved --live-approved
```

This uses only standalone tests/integration/compose.json, explicit project
 dincharya-m2c-synthetic and --env-file /dev/null. It verifies daemon/image pins,
refuses existing test resources, preserves unrelated container IDs, creates only
fresh isolated databases/roles, installs unchanged baseline plus0001–0009 and
checks SCRAM/container-local-trust/no-port/internal-network/read-only-root bounds.
Statement/error/parameter logging is suppressed before credential provisioning.
Only the named schema is accessed; no other backup/source search.

The launcher provisions separate owner/calculator/worker logins, pins the trusted
DB owner to the actual Telegram owner, and enables ONE synthetic birthday fixture
named success with a due time20 minutes ahead. No general calendar dates or user
astronomical rules are accepted. The real transport starts only through the
explicit live lifecycle host. getMe is the first live API operation; it must fail
closed on any bot/destination mismatch before polling begins.

The launcher prints only a restricted **gateway configuration path**, never its
contents. That file contains bot/HTTP authorization settings only; database-role
passwords and the server review-signing key remain in private process pipes.
The service/relays remain alive until the operator types STOP. Do not type STOP
until the gateway is stopped and evidence collected.

Terminal2, repository root, substitute the printed path (not secret values):

```bash
env -i PATH=/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 PYTHONPATH="$PWD" \
  /tmp/dincharya-m2g-runtime/bin/python -B telegram-gateway/gateway.py \
  --lunar-acceptance /tmp/PRINTED-DIRECTORY/acceptance.json --live-approved
```

No regular .env, production gateway configuration or other polling job is loaded.
The dedicated mode registers exactly one reminder job, not the old Gregorian
poller alongside it. SDK identity checks require owner user ID == private chat ID;
message body IDs and edited/bot/group/foreign commands do not grant authority.
The root formatter suppresses SDK/HTTP diagnostics and redacts the configured token.

## Exactly one owner-approved journey

1. In the pinned test bot's private chat, send `/lunar_birthday success` exactly once.
2. Confirm the preview is explicitly SYNTHETIC and the intended future fixture date,
   time, Purnimanta month/paksha/tithi and ordinary distinction are displayed.
3. Send `/approve_lunar_rule TOKEN` using the returned opaque token. This approves
   the rule only; it does not schedule a reminder.
4. Verify the separate occurrence preview/date/time and copy the occurrence UUID.
   Send `/approve_lunar TOKEN` using its distinct token. **Nothing is scheduled
   before this explicit occurrence approval.** Do not use old Gregorian decision
   commands or approve an unrelated request.
5. Send `/lunar_status UUID`; expect a projected event, no cancellation and pending
   delivery metadata (at most20 most recent records, no chat/message/token payload).
6. Keep the sole gateway polling job running until the displayed due time. It
   claims under PostgreSQL leases, sends plain text through TelegramReminders and
   records sent+receipt only after valid destination/message acknowledgement.
7. Confirm exactly one `Reminder: Synthetic lunar fixture: success` was received.
   Status must show sent, attempts1 and has_receipt=true. A preview/approval reply
   is not the reminder delivery.
8. Observe at least two more15-second polling intervals and inspect status again.
   There must be no second reminder. Do not submit another reminder as a retry.
9. Stop Terminal2 with Ctrl-C and allow graceful job shutdown. Only then type STOP
   in Terminal1. It prints sanitized state/attempt/receipt-presence counts, requires
   exactly one sent+acknowledged delivery and one series, then verifies full
   disposable teardown and unchanged unrelated container IDs.

Opaque review tokens expire after30 minutes. Changed/stale/expired reviews reject;
never silently substitute another date. If an approval reply is lost, inspect the
existing occurrence before retrying; do not create a replacement series.

## Rollback, failure and evidence

Before delivery, `/cancel_lunar UUID` proposes cancellation; it requires its own
`/approve_lunar TOKEN`. Confirm cancelled before stopping. Rejection uses
`/reject_lunar TOKEN` while the relevant proposal remains pending. No cancellation
can unsend a delivered reminder or rewrite sent/uncertain history.

If sending is in flight or outcome is unknown: stop further owner actions, collect
sanitized status and stop the gateway gracefully. Do not reset attempts, clear
leases, invoke resend/reconciliation or schedule a replacement. The worker
preserves uncertain outcomes and refuses blind replay. Definite rejection alone
follows existing bounded retry/backoff; any failed acceptance needs separate
owner review before another live attempt.

Terminal1 must remain alive until evidence/status is observed. STOP captures
sanitized summary before the disposable database is removed, including on failure.
Keep no raw chat/payload/token/credential/SQL dump in Git. Record only checkpoint,
bot identity verified flag, exactly-one owner confirmation, status/attempt/receipt
presence, final cleanup and unrelated-container invariance in the evidence report.
The token/owner credentials file stays restricted outside Git; revoke/rotate the
test token locally if exposed. No production rollback is needed because no
production resource is modified.

The launcher and real bot wire have not been executed live. Flag/credential gates
were tested offline; SDK/database/n8n/worker integration was tested with Telegram
IO simulated. Live confirmation remains the explicit next approval gate.
