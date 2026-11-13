# Milestone 2F — isolated in-memory personal recurrence contract

The implemented offline contract is committed/pushed at
`0304de6a5ee140c313eb4aae6c2d18a35b0e7e99` on
`development/m2f-memory-contract`. Historical results below are unchanged.
The separately authorized [PostgreSQL design](M2F_POSTGRESQL_DESIGN.md) now reviews
mapping, auth, transactions and differences; it implements no database behavior.

## Outcome and readiness

**The in-memory contract passes its focused acceptance.** It is ready for review
of a separately approved PostgreSQL adapter design and disposable synthetic SQL
acceptance plan. It is **not ready for executing a PostgreSQL migration/adapter,
production integration or live delivery**. Transaction, authentication, durable
identity mapping, conflict and concurrency design need approval first. Nothing
in this document grants those permissions or approves the astronomical engine.

29 focused tests passed in0.480s:15 adapter cases,2 research-comparison regressions,
12 existing reminder-worker tests (mock transport only). A strengthened stale
approval/unauthorized replay case passed separately in0.001s. Runtime uses the
existing pinned local Python/kernel only for one actual-engine adapter check.
No new astronomy experiments, reference rewrites, services, packages or downloads.

## Small contract and reused components

[memory_contract.py](../prototypes/panchang/memory_contract.py) is isolated under
prototypes, not imported by the gateway, n8n or worker. It has no database/transport
factory, environment loading, persistence, claim, finish, send, lease or retry API.
It cannot dispatch reminders. The existing worker's Repository contract is not
implemented and process_batch is never wired to it.

Reuses LunarRule, logical_key and the exact research-only reconcile_calculations
validation boundary. Reuses [DeliveryReceipt](../dincharya/reminders.py) validation
and representation for invented sent-history fixtures. Does not duplicate
astronomical/month/policy calculations or SQL claim/backoff/quarantine logic.
Additional adapter validation checks named-rule/identity consistency, explicit
policy, selected/sunrise dates, complete physical interval and batch integrity.
It validates shape/consistency, **not cryptographic engine origin or independent
astronomical accuracy**; input comes from the trusted research evaluator/test setup.

API:

| Operation | Semantics |
| --- | --- |
| MemoryContract(owner_capability=...) | Trusted test setup supplies an opaque in-process owner object. Identity equality authorizes decisions; no caller-supplied actor-name string. This is a simulation, not production authentication. |
| register(Series(UUID, kind)) | Frozen birthday or wedding_anniversary series. Re-registration identical is idempotent; same ID with different kind rejects. |
| submit(series_id, LunarRule, preview) | Validate all rows first; create immutable proposals only. No automatic approval, ledger materialization, rule activation or send. Empty preview is a no-op, never cancellation/fallback. |
| approve(proposal_id, principal=..., action_id=UUID, acknowledge_changes=False) | Explicit single-occurrence approval from owner capability. Fresh generation/observation required; changed snapshot needs explicit review acknowledgement. Action ID bound to exact command. |
| materialize(proposal_id) | Requires that exact approval and fresh snapshot. Insert one synthetic ledger entry or return the immutable existing identical logical occurrence. No reminder job or delivery claim created. |
| seed_history_for_test(...) | Trusted owner injects invented sent/uncertain history for an existing approved synthetic entry. Receipt uses DeliveryReceipt; terminal record cannot change. Not a send, acknowledgement or reconciliation API. |
| entries / histories / approvals | Immutable dataclass records/tuples; snapshots are canonical JSON strings. No mutable references are exposed. |

## Series-scoped identity and immutable approval

Fixtures define two invented immutable UUIDs: one birthday, one wedding anniversary.
Both deliberately share Shravana Shukla9 ordinary. Ledger key is
`(immutable_series_id, logical_key(lunar_identity_v2))`; identical calendar keys do
not collide across series. Neither selected Gregorian date nor ephemeris profile
is part of that ledger key. Different ordinary/Adhika occurrences retain distinct
calendar keys. A UUID/event-purpose registry cannot be repurposed by a proposal.

Proposal stores the whole rule, purpose/series, calendar identity, selected date,
profile, candidate series generation, per-occurrence observation version and raw
research evidence as immutable canonical JSON. Proposal ID binds the semantic
snapshot/generation; sub-second bracket differences from overlapping queries do
not create a different semantic observation. First exact evidence is retained.
Date/rule/profile changes create a new observation/proposal and require approval.
No approval is inherited by another occurrence or changed rule.

Candidate rule generations advance when a different valid rule is submitted.
This invalidates older pending decisions/materialization without editing any
approved occurrence. Observations advance on semantic recalculation changes;
A→B→A does not reactivate old approvals. Multiple rows of the same rule/batch
share a candidate generation, so approving one does not stale its siblings or
approve them. Invalid batches change no generation, proposal or ledger state.

Approval is a distinct frozen record with its own action UUID and exact snapshot.
Replaying the same action/command returns that record; different command or wrong
principal rejects. A replay is not materialization and cannot restore freshness.
Mutating the caller's preview or returned record cannot alter approval history.

## Recalculation, review and terminal history

Same series/calendar key/date/rule recalculation cannot insert a second occurrence.
An approved recalculation with a different profile still returns the original
ledger entry/provenance/approval; the newer approval remains separate history.
Overlapping windows deduplicate by semantic proposal/ledger identity, not by row
root timestamps. Changed birth interpretation, repeated policy, month selector or
intercalation choice is a changed rule, requiring fresh approval even on the same
date. Unapproved or stale proposals cannot materialize merely because a ledger
entry already exists under that key.

**Existing ledger entries are immutable, including planned entries.** Even after
explicit changed-date/rule approval, replacing a previously materialized entry
rejects for separate review. This contract deliberately does not implement update,
remove, explicit rejection decisions, cancellation, override, ledger replacement
or terminal-history migration.
Those need a later approved policy/design, not silent edits to an approved record.
No-date/empty submissions do not erase a previously approved event.

Invented sent and uncertain records are separate frozen fixture history. Same-date
recalculation, repeated submission and changed-date attempts preserve those exact
records and receipts. A terminal history fixture cannot transition or be replaced.
There is no delivery queue/claim/send path; recalculation cannot resend. This proves
in-memory invariants only, **not distributed exactly-once delivery or durable
receipt/lease preservation**. Worker behavior remains existing independent logic.

The research-only comparison helper still refuses any application approval/ledger
payload. Adapter does not pass its application records through that helper: it
uses it only to validate research preview envelopes before proposing anything.

## Acceptance matrix

| Required case | Result |
| --- | --- |
| Unapproved proposal cannot materialize | Pass; no ledger write |
| Repeated submission and decision replay | Pass; same semantic proposal/action |
| Same identity/date recalculation | Pass; one entry, original snapshot retained |
| Changed date | Pass; review acknowledgement required, existing entry never replaced |
| Changed birth interpretation/repetition | Pass; new candidate generation, fresh per-occurrence approval |
| Overlapping windows | Pass with synthetic bracket changes and actual engine windows |
| Birthday versus wedding same lunar key | Pass; distinct immutable series keys |
| Sent/uncertain records | Pass; exact immutable history/receipt preserved |
| Recalculation resend | No send/claim capability; no worker wired, no actual delivery |
| Unsupported/ambiguous/skipped/unselected dates | Pass; entire invalid batch rejected before mutation |
| Approval scope | Pass; one occurrence/action cannot approve another or changed rule |
| Research-only reconciliation boundary | Pass; application-state payloads reject |
| Additional auth/stale/ABA/atomicity | Pass; wrong owner, reused action, reverted observation and mixed invalid batch reject |

Red-before-fix evidence: a forged selected2030 date outside its supplied2023 tithi
interval was initially accepted. The focused test failed, then passed after adding
a Delhi civil-interval containment check. This is an input-consistency guard, not
an astronomical recalculation. Tests use synthetic date-shifted intervals when
modelling an alternate calculation; no accepted reference facts were changed.

[Fixtures](../tests/panchang/fixtures/memory-contract.synthetic.json) derive from
committed public/synthetic pre-integration results. Test series, owner capability,
receipt and history action IDs are invented. [Results](../prototypes/panchang/memory-contract-results.json)
record29 passes and SHA256 of11 unchanged accepted reference/result files.
No personal records, secrets or raw publications are in this commit.

## Relationship to existing approval/reminder contracts

Source-reviewed public.decide_gregorian_change uses caller/request ownership,
original event snapshots, row/advisory locks, guarded conflict checks and an
atomic SQL subtransaction. This simulation follows mandatory authorization,
snapshot freshness, idempotent decisions and no approval inheritance. It does
not claim SQL compatibility, concurrency, conflict detection or atomic crash
recovery. Candidate-rule invalidation at submit time is deliberately conservative
and differs from a committed SQL event edit; it is not an implemented series update.

The existing reminder worker retains leases/acknowledgement/retry/uncertainty
semantics in PostgreSQL. No alternative worker was built. Existing mock worker
regressions pass; they do not prove a lunar SQL-to-worker integration. The existing
one-event/date ledger and future series/calendar key mapping still need explicit
additive schema/slot compatibility review. No baseline or migration was opened or
executed beyond repository-owned SQL source inspection.

## Risks and next isolated stage

- Single process/thread, no durability or multi-process race protection. Store
  capacity caps reject instead of evicting history; process loss loses everything.
- Opaque owner capability is trusted test authority only; real DB login/HTTP
  authentication, actor binding and untrusted payload limits are not implemented.
- Preview origin/model accuracy is not authenticated. Existing60-second diagnostic
  failures, direct-Purnimanta/source-profile gaps and Kshaya limitations remain.
  Unsupported cases cannot enter this ledger; scheduling adoption remains disabled.
- No replacement/cancellation/conflict/in-flight-send policy or transaction locks.
  Epoch, observation, approval, ledger and receipt changes need atomic durable SQL
  design and adversarial concurrent tests before PostgreSQL execution.
- Legacy identity mapping, approved-profile upgrades and reminder notification-slot
  mapping are unresolved architecture gates. No automatic sent/uncertain reset.

**Recommend next:** owner-reviewed PostgreSQL adapter/mapping design and a finite
acceptance plan using only disposable synthetic data; approve role/authentication,
transaction/locking, uniqueness and immutable history rules before any actual DB
implementation/migration/testing. The offline contract is a useful input to that
review, not permission to begin it. No production/database/n8n/Telegram, deployment,
merge or other orchestrator work follows from this checkpoint.

Reproduce focused tests in the existing isolated pinned environment:

```bash
DINCHARYA_PUBLIC_DE440S=/EXTERNAL/PUBLIC/de440s.bsp \
  OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  /tmp/dincharya-panchang-repro/bin/python -B -m unittest \
  tests.panchang.test_memory_contract \
  tests.panchang.test_preintegration.PreintegrationTests.test_reconciliation_refuses_application_state \
  tests.panchang.test_preintegration.PreintegrationTests.test_changed_personal_policy_requires_review_even_same_date \
  tests.test_reminder_worker -v
```
