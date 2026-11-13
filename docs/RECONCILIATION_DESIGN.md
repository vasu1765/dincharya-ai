# Audited uncertain-delivery reconciliation — design for owner review

Resolution and resend are **not enabled**. There is no resolution function,
gateway command, resend queue or privileged operator grant in this patch.
Inspecting a record is not approval to change it. Owner approval is required
before enabling either a metadata resolution or any resend operation.

## Current receipt and inspection boundary

A successful Telegram send returns a validated chat/message pair. The normal
acknowledgement API requires the live claim token, sending status and unexpired
lease; it writes sent status and receipt in one transaction. Historical or legacy
acknowledgements without a known pair stay NULL. Unknown transport outcomes and
expired leases remain quarantined without automatic retry. A commit exception
can mean rollback OR an already committed acknowledgement: inspect the ledger,
never infer non-delivery from the client exception or missing receipt alone.

`list_quarantined(after_id=0, limit=20)` runs a read-only transaction, normalizes
the local timezone to UTC, and returns bounded metadata plus receipt presence and
a SHA-256 observation version over the current database row. The digest binds
event/date identity, status, attempts, timestamps, lease/token, payload and receipt
without returning their private contents. It is an optimistic state fence, not
authorization, an authenticated signature, proof of non-delivery or anonymization.
Treat real observations as private metadata; do not publish/log them. New row
columns, database-version serialization changes or any row mutation invalidate
an old observation. A future action must recompute using the same UTC convention.

## Proposed resolution workflow (requires approval before implementation/enabling)

1. Authenticate an explicit owner/operator using trusted application identity and
   least-privilege database access. Do not trust an actor ID supplied in a payload.
2. Inspect a fresh uncertain record, with event/date identity and observation
   version; show the absence of a receipt as uncertainty, never as permission to resend.
3. Collect a reason, explicit action approval and private evidence reference. For
   confirmed delivery, require owner-attested chat/message evidence tied to the
   intended destination. Do not invent a generic Telegram message lookup API or
   recover an ID by guessing from adjacent messages.
4. In one transaction, take the existing common transaction lock and a row lock,
   recheck status is uncertain, no active lease and the observation version still
   matches. Reject stale reviews and duplicate action IDs before any mutation.
5. Append an audit record and the permitted transition atomically. Proposed audit
   fields: immutable action UUID, delivery ID, authenticated actor identity,
   action/reason code, evidence reference/digest, observed version, before/after
   state versions, approval reference and server timestamp. Keep private evidence
   outside public logs. Audit rows must be append-only for the application role;
   no ordinary worker privilege may edit/delete them or perform operator resolution.
6. Replaying an action UUID returns its recorded result without another transition
   or send. Partial failure rolls back both audit and state mutation.

The initial action proposed for approval is **record confirmed already-sent**:
validate the destination/receipt, enforce receipt uniqueness, append audit and
mark sent without HTTP I/O. Normal acknowledgement cannot do this after lease
expiry; it must remain protected, with a separate explicitly authorized operator
path. Leaving a record quarantined remains the default. No action is implemented.

## Resend is a separate architectural and authorization gate

Absence of evidence cannot establish that Telegram did not accept a message.
Any resend requires a new explicit owner decision acknowledging duplicate risk,
verified destination, bounded validity and a single-use authorization. It must
preserve the original uncertain history; do not reset its status/attempt counter.
The existing event/date uniqueness intentionally prevents an extra ordinary
delivery row for the same occurrence. A separate linked attempt/outbox design,
with its own durable permit, claim/lease, receipt and audit identity, must be
reviewed before enabling resends. Resolution approval must not authorize a send.

Acceptance before enabling: unauthorized/stale/leased/sent/replayed operations
reject without writes; evidence/destination mismatches reject; concurrent reviews
have one winner; injected failures leave no partial audit/state transition;
append-only privileges hold; resolution performs no transport call. Resend needs
additional explicit approval and separate single-use/expiry/concurrency tests.

This design adds no production permission. Milestone 2 still includes broader
recovery, reviewed source adoption, Hindu Panchang and operational acceptance.
