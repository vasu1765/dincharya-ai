# PR-stack integration review checkpoint — 2026-11-22

## Scope and ancestry

Base: `d4c1706a912e468974f033e22cf6785eeb47be0c`, previously accepted PR #16.
The open drafts #4, #5 and #7–#16 form a linear dependent stack; the base is
51 commits ahead of `main`, zero behind. No force-push, main merge, branch
closure, deployment or prior acceptance replay is part of this review.

## Delivery-receipt finding and correction

`dincharya.reminders.process_batch` previously treated a transport returning
`None` as a successful send and finished the claim without a receipt. The
notification-slot SQL acknowledgement similarly permits a `sent` state with
null receipt fields. This is an untested edge-case risk, **not evidence** that
the accepted Stage 1 or Stage 2 paired receipts were missing.

The application-layer change now requires a valid `DeliveryReceipt` for every
successful transport return. Missing or malformed results are recorded as
`uncertain`, never `sent`, and cause `DeliveryUncertain` without an
automatic resend. Explicit `NotAccepted` outcomes remain retryable through
the existing bounded backoff. Storage-acknowledgement failures remain uncertain.

## Validation scope

Five new focused unit tests cover missing, malformed, valid, definitively
rejected and storage-failure outcomes. A standalone reproduction of the revised
worker function and test cases passed 5/5 offline. This is **not** a claim
that the full repository suite or native PostgreSQL/n8n integration was run
on the review branch. Those are pending integration gates.

No prior numbered migration was modified. SQL-level enforcement of the
receipt invariant and compatibility with legacy receipt-less pathways must be
reviewed separately before authoritative source promotion. Avoid a blanket
historical migration rewrite.

## Other observed boundaries

- `dincharya/lunar_service.py`: signed command envelope, 60-second bounded
  timestamp, distinct command/tick/review keys and isolated database logins.
- `dincharya/lunar_runtime.py`: rejects production DB names, uses owner-only
  configuration and requires explicit live approval and dedicated bot identity.
  It remains an acceptance runtime, not a general personal beta deployment.
- `workflows/m2g-lunar-acceptance.json`: inactive repository-owned Webhook
  and HTTP Request relay; standalone workflow import/publishing remains gated.
- `database/migrations/0011_synthetic_notification_slots.sql`: fixed
  search_path on SECURITY DEFINER functions, synthetic database checks and
  explicit role grants. Full privilege audit remains outstanding.
- `docs/M2B_SOURCE_ADOPTION.md`: owner artifact decisions still required
  before source promotion. Legacy private workflow bodies and Code-node
  history remain outside review.
- Stage 2 closed-lid, recovery-only, encrypted USB and independent restore
  evidence remains accepted within its documented scope, with observer-tail
  and USB-health qualifications retained.

## Integration recommendation

Run the repository's targeted reminder tests and source-safety scan, then one
small disposable database negative-case check if the SQL path needs adjustment.
Complete artifact-level source dispositions and review of gateway and database
privileges. Integrate sequentially into a development baseline only after a
reviewed decision. No live Telegram, automatic startup, production or main
merge follows from this branch.
