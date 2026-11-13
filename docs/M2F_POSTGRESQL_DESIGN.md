# Milestone 2F — PostgreSQL mapping, authorization and transaction proposal

**Design/review only. No schema, SQL behavior or integration is implemented here.**
Base `0304de6a5ee140c313eb4aae6c2d18a35b0e7e99` on
`development/m2f-memory-contract`; entry tree clean, HEAD/tracking/GitHub confirmed,
no open PR. The owner authorizes this design, not PostgreSQL connections, migrations,
Docker, workflows, activation or delivery. Git metadata remains read-only.

## Recommendation and scope

Reuse an **ordinary managed Gregorian one-off event as the civil projection of
one approved logical lunar occurrence**, not as the definition of its annual
recurrence. A birthday/wedding series lives in new lunar metadata. Each distinct
logical occurrence maps to one immutable projection event ID; its reviewed civil
date/time is the one-off rule. The lunar calculator remains bounded/offline and
only proposes observations. It does not become another scheduler or worker.

This deliberately avoids changing the occurrence generator's return shape,
Gregorian matching predicates, reminder event/date uniqueness, claim/finish APIs,
retry/backoff, leases, receipt acknowledgement or Python transport/worker. No new
queue or delivery ledger. It does require a new guarded decision coordinator,
metadata tables and protection of mapped projection events. Approval of this
mapping is an architectural gate, not implied by this document.

Initial proposed **synthetic PostgreSQL acceptance scope** is one reminder at the
approved event time for each occurrence. The current reminder code has one ledger
row per event/date and derives due_at directly from event date/time. Multiple
advance reminders or independent reminder-time offsets cannot be claimed from
that contract. Do not fake advance reminders as extra calendar events: that
would distort conflicts, identities and user-visible dates. Full Milestone 2 still
requires advance/slot design and acceptance. Owner must explicitly approve this
limited first test scope, or require slot design before implementation. Nothing
is enabled for general scheduling in either case.

## Repository facts and knowledge limits

| Source inspected | Relevant existing contract |
| --- | --- |
| [0001](../database/migrations/0001_gregorian_occurrences.sql) | schedule_events + recurrence_rules + schedule_occurrence_overrides; generate_event_occurrences; original snapshots; v2 proposal/decision/dispatch; global advisory lock; row locks; bounded conflicts and transactional rollback. |
| [0002](../database/migrations/0002_occurrence_reminders.sql) | Existing reminder_deliveries(event_id,occurrence_date) conflict target; managed_by=m2e queue; refresh/replan, pending/failed claim, five-attempt cap, live lease/token, uncertain quarantine and in-flight edit guards. |
| [0003](../database/migrations/0003_managed_legacy_boundary.sql) | Legacy submit/decision barriers for m2d-managed events, including previously pending requests; preserved original bodies. |
| [0004](../database/migrations/0004_telegram_receipts.sql) | Nullable paired receipts, unique chat/message identity; lease-checked atomic acknowledgement; unknown historical IDs remain NULL. |
| [0005](../database/migrations/0005_synthetic_reconciliation.sql) | Synthetic-only role separation, trusted session login mapping, fixed search_path, append-only audit/evidence; worker API wrappers. Not a production authorization framework. |
| [worker](../dincharya/reminders.py) / [adapters](../dincharya/reminder_adapters.py) | Injected claim/finish/send contracts; no retry after uncertain acknowledgement. Restricted worker wrapper is already an opt-in path. Existing proposal adapter passes user_id to public APIs; that is not the new trusted identity boundary. |
| [memory contract](M2F_MEMORY_CONTRACT.md) | Immutable series/calendar keys and snapshots; explicit single-occurrence approvals; semantic observation versions; candidate invalidation; immutable fake ledger/history. |

Only repository-owned sources were inspected. Full original baseline DDL, private
legacy bodies and production ACLs are not adopted in Git and were not accessed.
Do not invent FK targets for a user table, baseline constraint names or guaranteed
legacy entry-point coverage. Existing inserts/columns and ON CONFLICT targets
above establish the interfaces used here, not complete schema certification.
Before future runtime tests, require an explicitly authorized isolated schema
source and catalog/ACL verification. No private search or 2B adoption is implied.

## Data mapping and uniqueness

```
immutable lunar series UUID + typed lunar key v2
                    -> lunar occurrence UUID
                    -> one stable schedule_events.id
                    -> one managed Gregorian once recurrence_rules row
                    -> existing reminder_deliveries(event_id, occurrence_date)
```

Two user events with the same lunar date remain separate series, separate logical
occurrences and separate projection events. They can still conflict at the same
civil time; existing conflict checks require an explicit owner override, not
silent deduplication or a birthday-specific exemption.

Logical key v2 retains convention/month/ordinary-Adhika/lunation-cycle/paksha/tithi.
It excludes engine profile, selected Gregorian date, title and date-selection
policy. DB uniqueness must cover the **typed tuple plus series UUID**, not JSON
text formatting or a client hash alone. Canonical key/hash is a consistency aid;
SQL validates every typed field and compares the canonical snapshot. Any changed
key set, convention, name or cycle requires explicit mapping review. No automatic
v1 backfill, relabel or conversion of an existing Gregorian series.

Each logical occurrence keeps its projection event ID forever once allocated.
Date replacement must not allocate a new event and evade delivery history or
attempt limits. A cancelled occurrence remains a tombstone under the same unique
key; initial API offers no restore/recreate operation. The current event/date
reminder unique constraint remains intact. Gregorian events without a lunar
mapping behave exactly as before.

### Minimum proposed additive records

Names/types below are a review contract, **not executable DDL or a migration**.
Private metadata lives in lunar_private; callers use lunar_api only. Seven small
tables separate identities, immutable evidence and authority; request/queue tables
are reused rather than cloned.

| Proposed record | Fields and constraints |
| --- | --- |
| lunar_principals | role_oid + role_name binding to session_user; owner_subject bigint used as existing requested_by; kind owner/calculator; enabled defaults false; isolated_synthetic environment. Unique login binding, trusted fixture-admin provisioning only. No assumed baseline users FK. |
| lunar_profiles | profile_digest PK, immutable model/kernel/dependency/ayanamsa/horizon/location/guard/range specification, evidence version and isolated-test authorization. No runtime profile update; new spec means new digest. This authorizes a test fixture, not final astronomical adoption. |
| lunar_series | UUID PK, immutable owner_subject and birthday/wedding purpose; committed rule JSON, approved profile policy, committed revision bigint, accepting/enabled state. Draft revision0 can exist without any event. Rule/status changes only through reviewed decisions; before/after audit preserves every version. |
| lunar_occurrences | UUID PK; series FK; typed v2 logical tuple with one composite UNIQUE; monotone observation version/head and approved-revision pointer; projection_event_id bigint UNIQUE nullable FK schedule_events. Logical identity/owner/projection binding immutable; unapproved rows have no projection. |
| lunar_calculations | UUID PK; series FK, optional occurrence FK for unresolved inspection data; immutable profile FK, exact evidence, selected date or NULL, result/review reason, full rule/policy hash, producer identity, received sequence and content hash. Unique producer submission action + same-command replay. No date for unsupported cases. |
| lunar_approved_revisions | occurrence FK + revision PK; lunar request FK, optional child Gregorian request FK, calculation FK for a date selection, old/new civil selection, title/time/timezone/policy snapshot, cancelled flag, command/audit link. Append-only. Cancellation can reference prior calculation; never invent a new calculated date. |
| lunar_action_audit | action UUID PK; authenticated principal/owner, request FK, canonical command hash, decision/outcome, before/after revisions, projection request link, reviewed conflict hash/acknowledgements. Append-only UPDATE/DELETE/TRUNCATE denial. At most one final decision per request; denied/conflict attempts may be separate immutable outcomes. |

Reuse schedule_change_requests for pending/approved/rejected request lifecycle and
its event_id/proposed_data/requested_by/decided_at interface. A validated
`api_version=lunar-1` envelope stores operation, series/occurrence IDs, expected
committed revisions and observation, immutable calculation/profile/rule snapshots,
expected original projection, bounded scope and conflict-review information.
Freeze requester/action/desired/original data after insertion; only the trusted
decision coordinator can finalize status. New audit records preserve exact actions
and responses; do not treat mutable request status alone as an approval snapshot.

Pending request.event_id may be NULL before the occurrence's projection exists;
it is filled only with the approved projection ID. Do not use this one field as
series authorization. Source-owned series metadata supplies owner checks. DB
constraints/typed references, write barriers and transactional tests must enforce
snapshot relationships; a JSON tag is never authority.

No new occurrence override table, recurrence predicate or reminder table is
proposed. Immutable approved revisions express lunar changes; the one-off event
and rule are the mutable, guarded projection of the current approved revision.

## Proposed API boundary

Signatures are illustrative typed contracts, not implemented functions. No API
accepts actor/user_id as authority, mutable approved flags or a delivery status.

| API | Inputs and effect |
| --- | --- |
| lunar_api.propose_series | request action UUID, new immutable series UUID/purpose or existing series, expected committed revision, desired named personal rule/profile policy. Create/replay a pending request; no event or scheduling write. |
| lunar_api.record_calculation | producer submission UUID, series UUID, expected approved rule revision, validated profile/evidence and bounded logical/date observations. Append immutable observations and monotone heads; unresolved cases are inspection-only. No automatic request approval or projection. |
| lunar_api.propose_occurrence | request action UUID, occurrence/calculation IDs, operation select/replace/cancel, expected series/occurrence/observation versions, intended civil selection/title/time. Copy authoritative snapshots server-side. One occurrence per initial selection decision; no implicit approval of siblings or a rule change. |
| lunar_api.inspect_request | own pending request's immutable desired/original snapshots, current observation/revision, affected delivery-state summary and conflict-review result; sanitized inaccessible/foreign IDs. |
| lunar_api.decide | decision action UUID, request ID, approve/reject, exact expected request/revision/observation fingerprint, reviewed change acknowledgement, explicit conflict override + expected conflict hash if needed. Derive principal from login; authenticate before replay lookup; atomic finalization/projection/audit. |
| lunar_api.propose_series_cancel | explicit bounded manifest of every affected projection/occurrence version plus series head. Approval is explicitly for that entire reviewed manifest, not inferred from one occurrence. Above initial64 target bound, reject for a reviewed batch design; do not partly cancel. |

No separate public materialize-by-ID call: approval and eligible projection
materialization happen in the same DB transaction. Memory approve/materialize
separation was a test seam, not a persistence recommendation. Exact decision
replay returns its recorded result and never repeats materialization. Reusing an
action ID with a changed request, policy, force flag or principal rejects. A blocked
conflict leaves the request pending but records that action's immutable outcome;
retrying with new override/review is a new action, with fresh conflict/version
checks. A final request cannot get a second approve/reject decision.

Series-rule approval changes only the committed rule revision/profile policy.
It does **not** approve or rewrite any occurrence. Subsequent occurrence proposals
must bind that approved rule; existing historical projections retain their old
approved snapshot until an explicit per-occurrence action. Rule changes that
alter key interpretation require explicit identity mapping, not an automatic diff.

Calculator may append candidates only for its mapped owner's approved series.
DB validates field types, ranges, profile allowlist, rule/key consistency, finite
intervals, UTC/local interpretation and bounded payloads. It cannot certify the
physical astronomy from JSON. The trusted producer and owner review remain a
separate trust boundary; preserve unresolved date-withholding and the original
60-second diagnostic evidence. DB must not perform a new astronomical calculation.

## Reusing existing SQL without bypassing approval

For an approved selection with no projection, the trusted coordinator calls the
existing propose_gregorian_change(add,series,...) and decide_gregorian_change with
a **real once rule for that approved civil date**, derived owner and approved
payload. This subordinate request is created and decided inside the outer lunar
transaction; it is never exposed as an independently pending child. Record both
request IDs in the approved revision/audit. Check success values: false does not
mean a committed lunar approval. Any failure rolls back child event, rule, mapping,
revision, ledger changes and final status together. One explicit lunar owner
approval authorizes exactly this one civil projection, not other lunar dates.

For eligible replacement, reuse the same projection event ID and native v2 update.
0001 updates recurrence_rules.start_date but its update branch does not update
legacy schedule_events.event_date. The proposed trusted projection helper must
synchronize that compatibility column to the **same approved civil date** in the
same transaction; otherwise legacy display/state can be stale. This is a future
mapping obligation, not a database defect fixed in this checkpoint. No rule
calculation or conflict predicate is copied into the lunar adapter.

Existing generator, overrides and queue continue to see a Gregorian once event.
The annual lunar rule exists only in lunar_series, never in a pretend Gregorian
yearly rule or an unverified calendar_system enum literal. Unapproved calculations
are not visible to generate_event_occurrences or reminder refresh.

### Mandatory mutation barriers

A proposed mapping-aware guard must block direct legacy, generic v2, advanced-add
or raw table mutations of mapped events/rules/overrides outside the trusted lunar
coordinator, including requests pending before mapping. Existing0003 protects
m2d ownership but does not distinguish the new lunar sidecar from ordinary v2
requests. Its api_version=2 path must not become a lunar approval bypass.

Dispatcher must recognize lunar-1 before any legacy fallback, and unknown calendar
namespaces must reject. A public direct decide_gregorian_change call targeting a
mapped event must reject even if the caller spoofs requested_by or JSON version.
Only the NOLOGIN projection executor inside a validated lunar decision may make
the linked native change; ordinary logins cannot SET ROLE into that executor.
Do not authorize via caller-set GUCs or a public bypass helper. Deny arbitrary
projection linking/adoption; initial mappings can point only to events created
inside that same authorized transaction.

Protect the underlying tables as well as dispatch. Revoke ordinary direct DML
and PUBLIC execution of any new internal bypass helper. Preserve existing function
bodies/checksums; use a future separately reviewed additive guard/wrapper approach
and verify catalog security properties. No edited0001–0005 files in this design.
Unknown baseline mutation entry points are a catalog-review acceptance prerequisite,
not assumed safe because they are not visible in these repository migrations.

## Authorization and privileges

Synthetic first stage: separate calculator and owner decision logins mapped by
trusted role OID **and** name to one owner_subject; a second synthetic owner tests
cross-owner denial. session_user is authoritative even inside SECURITY DEFINER;
current_user alone would identify the executor. No p_user_id, SET ROLE string,
actor JSON or caller GUC establishes ownership. Revocation/disabled login checks
occur before request or action replay disclosure. Existing public caller-ID APIs
are not a suitable new lunar authorization boundary.

New schema/functions are not public. New executors are NOLOGIN, NOINHERIT,
NOSUPERUSER, NOBYPASSRLS with only required table/column/sequence/function rights;
no ordinary login is a member of an executor role. Safe fixed search_path with
pg_catalog first, fully qualified objects, no user-writable schema lookup or dynamic
SQL from identifiers/payloads. Bind adapter values as parameters. Append-only
records protected from UPDATE/DELETE/TRUNCATE; triggers are defense in depth, not
protection from superusers. Production auth/TLS/role rollout is not covered.

No enabled principals/profiles by default, and every new API restricted to the
explicit isolated synthetic database/environment in the first implementation.
Fixture administrator alone provisions test authority/profile rows. Do not reuse
0005 operator principals or grant lunar callers uncertain-delivery reconciliation
rights. Ordinary reminder worker remains limited to its existing lease APIs and
cannot propose, approve, edit lunar tables or alter audit/history. Its existing
executor needs no lunar-table reads with this projection design.

## Decisions, transactions and lock order

Use the existing transaction-level advisory lock `(20261112,1)` for all initial
cross-calendar mutations, refresh, claim and acknowledgement paths. This is the
existing scheduler mutex, not migration-renderer `(20261112,2)`. Do not introduce
an unrelated lunar mutex and claim it serializes the existing worker.

Lock order: scheduler advisory lock first; authoritative principal/profile rows
as needed; lunar series; requests/occurrences in deterministic UUID order;
projection events/rules and delivery rows in deterministic ID order. Native
Gregorian child functions take the same reentrant advisory lock and then their
own request/event locks. No caller may acquire those row locks and subsequently
wait for the scheduler mutex. Revoke raw DML paths; a row trigger alone cannot
establish the required order after a row lock was already acquired. Administrative
revocation/profile changes that take these locks need the same order.

Each proposal/observation/decision is one transaction. On selection decision:

1. Authenticate/authorize login and environment, acquire mutex and authoritative
   principal locks; resolve same-command action replay only after authentication.
2. Lock pending request, owner series, occurrence and relevant projection/delivery
   rows. Recheck committed rule/profile revision, request fingerprint, observation
   head and occurrence approved revision **after locks**. Monotone versions prevent
   ABA; timestamp equality is insufficient. Missing/unavailable/foreign IDs use a
   sanitized result without private schedule data.
3. Revalidate finite date/time, selected/review status and scope. Initial selection
   must be future work; historical preview queries do not authorize backdated jobs.
   Acknowledgements bind changed policy/date and any exact reviewed conflict set.
4. If permitted, create/update/cancel the native one-off projection under the same
   transaction using the existing Gregorian validator/decider. Recompute conflicts
   across native generated occurrences; forward explicit force only when the
   reviewed conflict fingerprint still matches. Do not bypass overnight/window bounds.
5. Append immutable approved revision, link projection, advance the occurrence
   pointer/committed versions and finalize request/action audit atomically. No
   externally visible intermediate approval or partially scheduled batch.
6. Commit before returning. Lost response is replayed by exact action ID; never
   automatically reissue with a new action ID or generate another event.

READ COMMITTED plus the shared scheduler mutex, row locks and unique constraints
is the proposed initial isolation discipline. A concurrent unique violation is
not silently ignored: verify owner/key/command exact equality for idempotent replay
or abort. Deadlock/serialization retry must repeat the whole transaction with
unchanged action ID and re-read snapshots; bounded retry on known transient DB
errors only. Business stale/conflict/authorization failures are not blind retries.
An outage between approval and materialization cannot split state because there
is no separate committed materialize step.

Unlike the memory contract, merely submitting an alternative rule does not change
a **committed** series revision. Pending candidate/observation generation is separate;
only owner rule approval advances the active rule. A newer semantic observation
can stale an unapproved occurrence proposal, while never editing an approved
projection. No-date observations are inspection-only, not implicit cancellation.

## Reviewed replacement, cancellation and history

| Existing delivery state for the projection (all dates) | Proposed behavior |
| --- | --- |
| No delivery row, or only pending/cancelled rows with attempts0 | Owner-reviewed replacement may change the one-off date/time using the same event ID and logical key. Cancel old pending rows before projection change; keep old rows/IDs. Native refresh may create the new-date pending row. |
| Any sending row, active **or expired** | Reject changes until normal worker quarantine/inspection stabilizes the outcome; do not clear the lease or rewrite payload. Existing trigger covers active leases; lunar coordinator intentionally checks any sending row. |
| Any attempted failed row, dead row, sent or uncertain row | No date/time replacement or allocation of a new projection. Requires future separately authorized reconciliation/policy; no attempt reset or automatic resend. |
| Same key/date/time/rule, different approved calculation provenance | Idempotent projection; keep original delivery/approval history. Append calculation/action annotation only; do not refresh payload or reactivate cancelled work. No rematerialization under a new event ID. |
| Cancellation with no sending row | Explicit cancellation revision disables the one-off event. Existing refresh can cancel pending/definitively failed work; preserve attempt counters. Sent/uncertain/dead rows remain byte-identical. Cancellation is not undoing an external send. |
| Cancelled logical key | Tombstone remains unique, projection ID retained; initial API has no restore/recreate command. Future restoration must not reset attempts or terminal history. |

Replacement gate checks **all** reminder_deliveries for the projection event,
not only the current selected date. This closes the new-date/new-row retry-cap
and duplicate-send hole that event/date uniqueness alone cannot close. Initial
replacement is deliberately more conservative than ordinary Gregorian edits.
Cancellation of attempted/terminal work may stop future scheduling but cannot
claim unsending; a stable uncertain record can still be reconciled only through
its separately authorized existing operator process, never a lunar API.

Native refresh can revive cancelled rows when the same event/date becomes desired
again. Therefore prevent projection recreation/re-enablement outside a future
explicit restore policy; keeping a cancelled ledger status alone is insufficient.
Old snapshots must be stale after cancellation. Cancel-series must atomically
close future approval/materialization and disable the entire explicitly reviewed
projection manifest, or roll back all of it (including if one send is in flight).
No partial series cancellation presented as complete success.

Acknowledgement, receipt uniqueness and uncertain-resolution APIs remain unchanged.
A sent/uncertain row is never moved to a new occurrence/date or deleted. No historic
receipt backfill, claim token reset, operator action or resend flag is introduced.
Single at-event slot is the initial test limitation; multiple advance slots require
another explicit compatibility design before Milestone 2 closure.

## Memory-contract differences: design gaps, not silent implementation changes

| In-memory behavior | Proposed persistent semantics |
| --- | --- |
| Object capability; caller controls one process | Trusted login mapping/roles and table ACLs; authentic owner before replay. |
| Candidate rule change invalidates generation during submit | Separate pending observations from committed rule revision; owner approval alone changes active rule. |
| Approve then separate materialize | One atomic decision/projection/audit transaction; replay returns committed result only. |
| No explicit reject/cancel/replace | Pending request reject; reviewed cancellation/tombstones; narrowly gated never-attempted replacement. |
| Already materialized entry cannot change even before any attempt | Preserve immutable revisions, but allow approved unattempted projection replacement. Terminal history still immutable. |
| No conflict logic, in-flight checks or concurrency | Native conflict decision plus shared scheduler mutex/row locks and complete delivery-state gate. |
| Semantic signature binds rule/date/profile; subsecond evidence not proposal identity | Retain behavior for duplicate calculation replay, but persist raw provenance and monotone observations; never trust a supplied hash as authorization. |
| Terminal fixtures seeded by test method | No caller seeding endpoint; real worker acknowledgement and independently authorized operator recovery only. |

Offline source review found no further demonstrated defect within the **authorized
single-thread trusted in-memory scope** requiring a code patch. These differences
are reasons not to copy that model into SQL unchanged. No database behavior or
accepted prototype/evidence bytes were changed to make the design look complete.

## Finite synthetic PostgreSQL acceptance plan (not executed)

Prerequisites: explicit owner approval of mapping/policies/implementation and a
separate permission for disposable PostgreSQL execution. Use the existing pinned
isolated harness only, verify daemon identity and unrelated container invariance,
SCRAM/session-only credentials with no logs/argv/repository leakage, no ports or
production compose/volumes. Authorize exact schema source/catalog validation then;
no baseline/private artifact access now. Reject if isolation or unreviewed legacy
entry points cannot be verified. No n8n/Telegram/network transport, even in tests.

Use two synthetic birthday/wedding series sharing a logical date, another owner
for denial, pinned calculation fixtures and a bounded8-occurrence manifest. API
creation tests use future civil dates relative to server time. Worker/history
races use administrator-seeded, previously approved past-due synthetic projections
and **one server clock**. Do not mix a future p_now with now()-based edit guards
and call that a faithful lease-race test. No long sleeps: controlled expired leases
and multi-session barriers establish ordering. Claim/finish outcomes are synthetic;
never invoke a real send adapter.

| ID | Setup/action | Required invariant/evidence |
| --- | --- | --- |
| T00 | Fresh fixture/catalog/profile/role checks | Exact authorized schema, no PUBLIC/role escape, unchanged0001–0005 bytes and unrelated services. |
| T01 | Calculator, owner, worker, foreign owner, revoked login | Only mapped submit/decision rights; no arbitrary user ID, SET ROLE/GUC or foreign request disclosure. |
| T02 | Malformed JSON/key/profile, injection-shaped values | Typed validation and parameters reject safely; no dynamic identifiers or partial observations/events. |
| T03 | New series rule proposal / reject / approve | No projection before occurrence approval; committed rule advances only on explicit decision. |
| T04 | Same logical key overlapping submissions, two sessions | One series-scoped occurrence; replay exact observation; no duplicate request/projection. |
| T05 | Birthday and wedding same lunar key/time | Distinct events; native conflict surfaced and explicit reviewed override needed. |
| T06 | Approve one of ordinary/Adhika siblings | Other occurrence stays unapproved/unprojected; neither profile nor rule approval expands scope. |
| T07 | Simultaneous approve/reject or two approvals | Exactly one final decision/action outcome; no split projection, same-command replay deterministic. |
| T08 | Rule/observation A→B→A, stale snapshots | Old request cannot approve after committed/observed generation changes; pending-only rule proposal does not edit active state. |
| T09 | Changed birth basis/repetition/profile, same date | Fresh explicit snapshot approval required; no duplicate projection or silent approved-policy rewrite. |
| T10 | Inject failure after child event, revision or audit write | Full outer rollback, no approved request without projection or orphan native child request; bounded retry reuses action ID. |
| T11 | Commit succeeds but response lost | Exact action replay returns existing projection; changed command/principal same action rejects. |
| T12 | Pending attempts0 date/time replacement | Same event ID/key; old pending row cancelled, new native date generated; parent event_date and once-rule start_date synchronized. |
| T13 | Old date sent/uncertain/failed-attempted/dead, propose new date | Replacement blocked across all ledger dates; byte-identical sent/uncertain/dead/receipt and no new event/delivery. |
| T14 | Owner cancellation, repeated refresh/lookback/restart | Projection disabled; no cancelled-row revival, no fallback/restore/new attempt; versions stale prior requests. |
| T15 | Cancel series manifest with one live send / new projection race | Entire batch blocked or exact all-or-nothing cancellation; no partial result; future approvals closed atomically. |
| T16 | Direct legacy/v2/advanced/old pending mutations on mapped event | Bypass rejected at submit/decision/table boundaries, regardless JSON version or caller IDs; ordinary Gregorian controls still work. |
| T17 | Two workers claim same due work | Existing global lock/row SKIP LOCKED behavior; one live token per delivery, correct five-attempt semantics, no duplicated claim. |
| T18 | Claim versus date change/cancel in both controlled orders | Claim first blocks edit; edit first prevents obsolete claim; all delivery-state checks occur after locks. |
| T19 | Expired sending lease and stale acknowledgement | Change blocked until existing quarantine; old token acknowledgement false; no reset/replay. |
| T20 | Definitive not_accepted retry, cap, uncertain result | Existing bounded backoff/five attempts/uncertain quarantine unchanged; no lunar reset or new-date escape. |
| T21 | Synthetic sent acknowledgement with receipt / receipt collision | Existing lease check and receipt atomicity; duplicate receipt rolls back, no partially sent state. |
| T22 | Existing Gregorian event, override, cancel and legacy history | Native occurrence/date/conflict/reminder results unchanged; no accidental lunar routing/adoption. |
| T23 | Kshaya, unsupported/no selected/skipped/near-boundary input | Inspection/proposal refusal only, zero projection/reminder; repeated-date policy explicit and approved. |
| T24 | Profile upgrade/key rename/cycle or convention change | Same-key same-date annotation only, no resend; changed key set requires explicit mapping review, no auto-new event. |
| T25 | Attempt DML/DELETE/TRUNCATE audit/profile/evidence by ordinary roles | Privilege/immutability denial; worker cannot change rule/profile/approval or call operator recovery. |
| T26 | Post-rollback/cancellation/restart durable state inspection | Uniqueness, audit/snapshot/series mapping, terminal histories and attempts survive; no automatic resume/send outside approved workflow. |

Run each new case once, rerun only materially affected failures. Existing successful
n8n/live Telegram/2C acceptance is not part of this plan. Record sanitized assertions,
row/state fingerprints, transaction winners, cleanup and unchanged unrelated
container IDs. Expected outcomes above are **not claimed runtime passes**.

## Risk and owner decision matrix

| Decision/risk | Recommendation | Approval gate |
| --- | --- | --- |
| Projection architecture | One native once event per logical occurrence; stable mapping, no second generator/worker | Approve before implementation. |
| First test reminder scope | One at-event slot only; advance/multiple slots remain a Milestone2 blocker | Explicit scope approval or require full slot design first. |
| New records/authority | Seven metadata/authority tables, existing request/queue reuse, isolated-only roles/profiles | Review minimal schema, principals and trusted producer model. |
| Date/time replacement | Only never-attempted projections; same event ID; all-date history gate | Approve conservative restriction and immutable cancellation tombstones. |
| Cancel-series scope | Explicit atomic bounded manifest, not implicit per-occurrence approval | Approve initial64 cap/series semantics; no partial cancellation. |
| Rule/approval semantics | Committed revision on approval; atomic decision+projection; audit-only profile annotation when identical | Approve differences from memory contract. |
| Canonical identity/v1 adoption | Typed v2 tuple + immutable series UUID; no automatic historical mapping | Approve identity contract/mapping policy separately before any adoption. |
| Legacy/raw privilege holes | Catalog review, mapped-event guards and no direct DML/bypass executor membership | Block tests/implementation completion if unverified. |
| Clock/worker races | Shared scheduler mutex first and server-clock fixtures | Must pass concurrent claim/edit/expiry tests. |
| External astronomy evidence | Retain failed60s diagnostics and qualified date coverage | No scheduling/engine adoption from SQL test success. |
| Baseline/provenance gap | Future explicit isolated schema authorization, no private searches now | Not production source adoption or2B completion. |

No owner decision is required to finish reading this proposal. **Approval of the
choices above is required before implementation**, then separate authorization for
disposable database execution. Production auth/deployment, workflow wiring,
multiple reminder slots, broader calendar acceptance and main merge remain later
explicit gates. Neutral user profile and future consolidated named Smarta/Vaishnava
observance design stay intact; no festival calculations are introduced.
