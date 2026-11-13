# M2F synthetic end-to-end journey — passed

## Scope and Git state

Clean entry at pushed `5cf007f536aaaac2708238f20b1add10f2c27489` on
`development/m2f-postgres-integration`. Owner created and agent verified
`development/m2f-synthetic-e2e`. Git metadata is still mounted read-only; new
source/evidence is uncommitted. HANDOFF has consolidated safe commit instructions.
No Git bypass or remote-file substitution. No open PR exists for this branch yet.

Owner authorized a working isolated synthetic journey, not a live Telegram test,
production, deployment or merge. Scoped sandbox permission was granted for the
new command using the existing standalone2C stack. **E01–E05 passed, exit0;46
focused offline tests passed.** The successful T00–T26 suite was not repeated.

## Components and actual data path

```text
invented private gateway envelope
  -> real active n8n Webhook -> HTTP Request
  -> internal HTTP/stdio test bridge -> separate Python process
  -> SyntheticLunarPostgres -> real scoped SCRAM PostgreSQL sessions
  -> approved native Gregorian once projection
  -> PostgresReminders + process_batch
  -> deterministic SimulatedTelegram -> append-only attempt/receipt journal
  -> existing lease-checked acknowledgement -> existing reminder_deliveries
```

The gateway's private-owner envelope and explicit command/decision pattern were
reviewed and reused, but the live gateway is unchanged and not registered/running.
The new n8n workflow is entirely synthetic, with only native Webhook/HTTP Request
nodes. No Code, external HTTP endpoints, schedule trigger or parallel delivery
worker is introduced. The test controller requests ticks like the gateway's
existing polling job; PostgreSQL remains the authority for due work, claims,
leases, retries, identities and acknowledgements. This test does not certify an
automatic n8n cadence or a deployed polling service.

The Python subprocess directly uses the committed SyntheticLunarPostgres,
PostgresReminders(restricted_worker=True), process_batch and DeliveryReceipt.
Actual SQL transitions and n8n/Python executions are exercised; only Telegram
delivery is simulated. The simulated transport appends EVERY attempted send to a real PostgreSQL journal;
it intentionally has no dedupe that could conceal a worker defect. Success
returns a deterministic journal message ID, definitive failure raises NotAccepted,
and accepted-but-response-lost raises an uncertainty error. Existing worker code
persists the corresponding outcomes. No Telegram API client/network call occurs.

A test-only PsqlConnection provides the existing adapters' single-statement
execute/fetch/context protocol through actual psql sessions in the disposable
container. Values are separately escaped as literals with standard strings on;
only one static SELECT is supported. The transaction must commit before any
result is returned; failed psql/commit output cannot become success. This is
instrumentation, not a new production driver. Roles authenticate with SCRAM via
container-loopback TCP; owner, calculator, worker and journal transport use
separate scoped logins. No arbitrary actor ID selects the database principal.
The trusted harness/process has Docker control and test-only credentials; it is
not claimed to be a production process-isolation/authentication boundary.

The HTTP bridge only forwards RPC messages over private subprocess pipes. It
cannot schedule, approve, claim or deliver on its own. It listens only inside the
isolated existing mock-services container, authenticates its synthetic downstream
header, bounds requests and never logs bodies. Credentials/configuration go via
stdin or inherited environment, never secret argv values or repository files.
The native workflow/header and n8n session data exist only in disposable storage.
The n8n ingress envelope is intentionally fabricated by the trusted test harness;
body user_id/chat_id checks do not establish production Telegram identity.

## Fixture and approval semantics

Fixture builder uses the same invented Chaitra/Shukla5 ordinary lunar-key shape
as the accepted PostgreSQL fixtures, with distinct immutable series/action UUIDs.
Dates/times are deliberately selected from the real server clock, not astronomy.
The immutable profile explicitly declares astronomy_enabled=false. No engine,
ephemeris, predictions or previously accepted reference evidence is changed/read.

Each request produces a labelled synthetic preview before an event exists.
Explicit rule approval precedes calculation persistence/occurrence proposal;
separate occurrence approval binds the exact reviewed fingerprint. The request
alone, rule approval alone, stale decision or rejected request cannot schedule an
occurrence. A cancellation has its own proposal and explicit reviewed approval.

Six fixture paths: success, rejected, stale, cancelled, failure and uncertain.
The approved delivery times differ by milliseconds to avoid creating artificial
calendar conflicts; no forced approval or conflict bypass is used. Due work uses
real server/host UTC clocks, with no lease reset, backdated projection rewrite,
manual ledger seeding or fake future claim time. The wait is bounded.

## Actual runtime evidence

| Gate | Observed pass |
| --- | --- |
| E01 | Fresh schema/migrations0001–0008, SCRAM scoped roles, new Python process, actual active native n8n webhook. |
| E02 | Preview, explicit separate approvals, repeated request idempotency, unapproved isolation, stale/rejected decisions, approved cancellation and foreign-envelope refusal. |
| E03 | Stop/recreate Python process, restart only disposable n8n, recover active route with PostgreSQL container ID/start time unchanged. |
| E04 | Concurrent tick requests use existing worker/SQL claims. Success sent+paired receipt+attempts1; definitive rejection failed; accepted-but-lost response uncertain. Exactly one journal attempt for each of three eligible deliveries; none for other paths. Failed work explicitly cancelled, preserving attempts. |
| E05 | Second real worker/n8n restart, repeated ticks, journal still exactly3, exact delivery-history bytes unchanged, no resend/reset, failed attempt count retained and PostgreSQL unchanged. |
| Cleanup | Compose teardown removed only dincharya-m2c-synthetic containers/network; original unrelated running-container ID set unchanged; process workers stopped. Exit0. |

Condensed successful output (each gate emitted once):

```text
Starting pinned disposable synthetic stack
Three healthy services; runtime isolation verified
PASS E01 isolated schema, SCRAM roles, real component process and native n8n webhook
PASS E02 preview, separate approvals, idempotency, rejection/staleness and cancellation
PASS E03 actual worker-process/n8n restart, PostgreSQL unchanged
PASS E04 existing process_batch/SQL claims/simulated delivery/receipts and failure quarantine
PASS E05 durable restart recovery, duplicate suppression and exact delivery history
Removing only the disposable integration project
Teardown verified; original running container IDs unchanged
exit status 0
```

## Demonstrated failure and security correction

First runtime attempt stopped at the authentication assertion: the older Compose
fixture's initdb defaults left TCP loopback rules as trust. It verified teardown
and unchanged unrelated containers. The check was retained, not relaxed.

Only the disposable postgres-test environment was changed to include
`POSTGRES_INITDB_ARGS=--auth-local=trust --auth-host=scram-sha-256`. The full reviewed
Compose digest is now
`2b24c44fcebefd4f73824a4b1e3cfb8331c4dc99d8b8df509786e97217fb8a28`.
The pinned validator and affected offline tests pass. Local trust is confined to
the container Unix socket; TCP requires SCRAM. No existing service or production
Compose file changed. All other fixture limits, images, mounts, internal network,
project, no-port/read-only policies and configuration validation are retained.

Server statement/error/parameter logging was disabled and verified before any
credential SQL provision. Generated passwords/keys remain session-only and were
not printed, committed or included as command-line values. Private schema access
was restricted to the one authorized file, validated unchanged before cleanup.
No other backups, production credentials, 2B manifest, live Telegram/n8n service,
paid API, deployment or main merge was accessed/executed.

## Reproduce only when materially needed

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B tests/integration/synthetic_e2e_runner.py \
  --baseline /home/vasu1765/dincharya-backups/baseline-20261112T132918Z-d5V7Hf/application-schema.sql \
  --expected-daemon-id 44c1ef83-c50e-4ecc-8f19-4b112bc40f29 \
  --execute-approved
```

Uses only tests/integration/compose.json, project dincharya-m2c-synthetic,
--env-file /dev/null, existing pinned local PostgreSQL17/n8n2.47.3 images and
session-only generated credentials. Refuses pre-existing test resources and
checks daemon identity before creation. No new image/package is installed.

Offline checks:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_synthetic_e2e tests.test_integration_runner -v
```

46 tests pass (7 new scaffold/security tests and39 affected existing runner tests).
Includes literal/parameter safety, no success after failed commit, no-runtime
gate, foreign envelopes, no Code/second scheduler and inherited isolation checks.
AST/JSON/SQL framing, Markdown links and diff checks pass.14 of15 explicit safe-file
scans pass. The unchanged credential-generation/reference expressions in the shared
runner trigger two pre-existing potential-secret matches (lines268/296), also
present in committed HEAD. Human review confirms variables, not credential values;
its only diff is the reviewed Compose digest. Scanner rules were not weakened and
that file’s scan is not reported as passing. Existing application migrations, worker,
adapters, gateway, astronomical model and acceptance fixtures are unchanged.

## Blockers before the first private Telegram test

The synthetic journey is complete, with no unresolved runtime failure. A private
bot test still requires a reviewed real gateway lunar-command binding and trusted
upstream owner authentication; the fabricated envelope/test bridge is insufficient.
Replace test Docker/psql/stdio instrumentation with the real connection/transport
integration, retain distinct authenticated SQL roles and bind exact preview/rule/
occurrence approvals. Review webhook authentication and single tick ownership.

Then obtain explicit authorization for one dedicated test-bot/private-chat delivery
against a fresh disposable DB. Enter any replacement token/owner credentials via
a restricted local secret file outside Git; verify bot identity/isolation and wait
for explicit Telegram approval before scheduling. No credential file was accessed
or token requested at this checkpoint. No real sends are currently authorized.

That first test can remain fixture-only; actual Hindu-calendar scheduling still
requires separate engine/date acceptance. Advance/multiple reminder slots,
production provenance/ACL/operational adoption and other orchestrators remain
outside this checkpoint. Nothing here enables general astronomical scheduling.
