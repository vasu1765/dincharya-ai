# Audited uncertain-delivery reconciliation

The owner approved implementing and testing **record confirmed already-delivered
in isolated synthetic PostgreSQL only**. Migration 0005 and the Python operator
API implement that scope. Production reconciliation stays disabled. No Telegram
calls, resend/reset operation, gateway resolution command or production role
provisioning is added. See [verified evidence](M2_RECONCILIATION_RESULTS.md).

## Existing receipt boundary

Normal acknowledgement still requires the live claim token, sending status and
unexpired lease, and atomically stores sent state plus the nullable chat/message
pair. Unknown historical IDs remain NULL. A commit exception can hide an already
committed acknowledgement: inspect durable state; never infer non-delivery from
an exception or absent receipt. Unknown outcomes remain quarantined.

Read-only inspection returns bounded metadata and a SHA-256 observation version
of the full row serialized in UTC. It returns no payload, title, chat, token or
error text. The digest is a state fence, not authorization, anonymization, proof
of delivery or proof of non-delivery. Row or serialization changes invalidate it.
Real observations and evidence must remain private.

## Identity and least privilege

0005 refuses installation outside `dincharya_app_test` by `synthetic_test`, or if
its fixed cluster roles already exist. The migration renderer wraps installation
and its checksum ledger in one transaction. The private synthetic gate defaults
to disabled; fixtures enable it temporarily and disable it before teardown.

| Principal | Granted boundary |
| --- | --- |
| Trusted fixture administrator | Registers login name/OID and private destination; provisions independent delivery destination pins, verified evidence and explicit expiring permits; controls the synthetic gate. |
| Operator login | Member of operator group; executes inspection and confirmed-delivered API only; cannot provision evidence/permits, enable the gate, mutate the ledger/audit directly or use worker wrappers. |
| Reminder-worker login | Executes lease-checked claim/finish/acknowledgement wrappers only; no direct ledger writes or reconciliation/private-table access. |
| NOLOGIN reconciliation executor | Owns fixed-path SECURITY DEFINER functions; can read required records, update only four delivery columns and insert audit. Narrow identity-column UPDATE grants allow configuration row locks. No caller is a member. |
| NOLOGIN worker executor | Owns separate worker wrappers and has the table/sequence privileges needed by unchanged invoker-security worker functions. No caller is a member. |

Identity comes from authenticated PostgreSQL `SESSION_USER`, bound by both role
OID and name, never a request actor ID, custom setting or `SET ROLE`. A login with
both operator and worker memberships cannot reconcile. Callers cannot assume an
executor role or another session identity. All new SECURITY DEFINER functions
have a fixed `pg_catalog,pg_temp` search path and qualified application objects;
PUBLIC execution/schema access is revoked. The Python worker's restricted mode
uses only a boolean-selected constant schema; default operation is unchanged.

## Evidence and authorization

The administrator independently pins the intended destination for each delivery.
A private immutable evidence record binds delivery, positive chat/message IDs,
finite delivery timestamp, evidence UUID and SHA-256 digest, plus an attestation.
The operator cannot create or modify it. An immutable approved permit binds the
same delivery/evidence, action UUID, operator OID, observation version, exact reason
and expiry. The request must independently set `confirmed=true` and match the
operator destination, destination pin, evidence and permit. Evidence time cannot
be in the future or precede the last claim.

Validation establishes consistency with trusted attestations, not the truth of
an external Telegram receipt. Tests use invented evidence only. No Telegram
message lookup, cryptographic receipt authentication, external evidence ingestion
or production evidence-authority workflow is implemented. A real authority and
secure provisioning/review process require separate design and owner approval.

## Atomic resolution and replay

`OperatorReconciliation.record_confirmed(ConfirmedDelivery(...))` makes one
parameterized SQL call with no actor field. The database:

1. Authenticates membership, takes the existing common transaction advisory lock,
   and locks enabled gate/principal configuration rows against concurrent changes.
2. Validates explicit confirmation and bound inputs. An exact previously committed
   action returns its prior result with `replayed=true`, without any new writes.
   A changed command with the same action ID rejects.
3. Requires the approved unexpired permit, independent destination pin and verified
   evidence; locks the delivery row and rechecks permit expiry **after waiting**.
4. Requires an `m2e` uncertain row with a prior attempt/claim, no worker token or
   lease, no existing receipt, and a fresh UTC observation version.
5. Updates only status, sent timestamp and chat/message IDs, and appends the audit
   row in one subtransaction. Unique receipt/action/authorization/delivery fences
   prevent duplicate transitions. An audit or state-write failure rolls back both.

Audit includes authenticated login/OID, reason, evidence reference/digest,
approval/action identity, receipt, before/after versions, request hash and server
time. Application roles cannot update/delete/truncate audit, evidence, permits or
destination pins; immutable triggers add a second guard. Attempts, claim/retry
history, payload and other columns remain unchanged. Caller rollback also undoes
both writes. A client commit error yields a sanitized unknown result and no
automatic retry: inspect or explicitly replay the **same** action and command.
An exact committed replay still requires an enabled principal/gate, but does not
consume a fresh permit or change state after the original permit expires.

## Synthetic credential boundary

The disposable server explicitly uses SCRAM for TCP localhost; actors authenticate
as distinct non-superuser logins. Unix-socket trust is confined to fixture-admin
commands inside the no-network container. A wrong-password test proves TCP does
not silently fall back to trust. Session-only random passwords travel through
stdin for provisioning and inherited environment variables for authentication,
never values in command arguments or repository files. Diagnostic output is
captured and sanitized. Server statement, duration, sampling and parameter logging
are disabled, including error-statement logging below PANIC. The review test
checks effective settings. No raw Docker inspect or PostgreSQL logs are printed.
Trusted host/daemon/database administrators can inspect memory/container
environments or alter logging/ACLs; this is not protection against those actors.

## Remaining gates and limitations

This is a synthetic API/ACL proof, not production readiness or multi-tenant
isolation. Original migrations 0001–0004 and baseline bytes are unchanged; 0005
adds optional synthetic roles/APIs and no historical backfill. Production gateway
startup still requires only the existing four migrations. No deployed service is
rewired. The fixed synthetic roles require a fresh cluster, not a shared server.

Evidence retention/revocation procedures, trusted real destination/evidence/permit
provisioning, production roles/authentication/TLS, operator UX, deadlock/timeouts
and operational recovery remain review work. Application append-only guarantees
do not withstand a trusted superuser dropping triggers or changing definitions.
Global advisory locking serializes operator decisions and can limit throughput.
No external exactly-once guarantee is claimed.

Resend remains a separate architecture and owner-authorization gate. Absence of
proof never authorizes sending. Any future resend needs its own durable single-use
permit, linked attempt/outbox, lease, receipt and audit design; do not reset
uncertain attempts or reuse resolution approval. All Milestone 2, including Hindu
Panchang and operational acceptance, still precedes other orchestrators.
