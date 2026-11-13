# Development decisions

These decisions record reviewed source/evidence and constraints. They do not
provide fresh approval to access private inputs or operate services. See
[architecture](ARCHITECTURE.md), [roadmap](ROADMAP.md) and [policy](DEVELOPMENT_POLICY.md).

## D01 — Finish Milestone 2 before expanding domains

Owner reconfirmed 2026-11-13: complete ALL Milestone 2, including source adoption,
Gregorian recurrence, reminders, Hindu Panchang scheduling and operational
acceptance before Adhyayan, Arogya, Atma-Chintan, Vittiya or other orchestrators.
Production access and deployment still require separate approval. See
[MILESTONE2_PLAN.md](MILESTONE2_PLAN.md). Offline preparatory work can
continue autonomously; new feature scope and operational gates remain explicit.

## D02 — Separate private preparation from Git adoption

Accepted. Raw backups, SQL records, workflow bodies, identities, personal data,
credential mappings and source evidence remain outside Git. Preparation requires
explicit input paths and restrictive permissions, never recursive backup discovery
or automatic promotion. Scanners are heuristic; human review remains necessary.
Private files are not encrypted merely because their modes are 700/600. Temporary
reports are not durable backups. Integrity hashes are unsigned and not authentication.

## D03 — Preserve originals; compare JSON structurally

Accepted. SQL and Code bodies must be byte-preserved; do not regex-rewrite functions,
triggers or JS. For comparisons only, JSON object-key ordering is ignored because
jsonb snapshots can reorder keys. Arrays, scalar types, strings/Code and parameter
values remain significant. A serialization-order mismatch is not a workflow change.
The corrected comparison is covered by regression tests; originals remain separate.

## D04 — Keep current, publication reference and historical body distinct

Accepted. Resolve exact version references against authorized history records;
never select a latest-looking event or substitute editor content as a published
body. Preserve identifiers privately. Versionless events are retained without
inventing IDs. All four current node/connection bodies match same-version history.
The located published body differs by a node position, with matching parameters,
Code and connections. This does not prove runtime equivalence or executing version.
Historical settings/staticData are absent from the reviewed history layout and
are not filled from current configuration. Only the approved three tables were
extracted; credential/execution-table access is excluded.

## D05 — Scheduler fields are native, significant state

Accepted for the exact reviewed image: n8n 2.47.3, packaged n8n-nodes-base 2.47.2.
recurrenceRules stores last-run gating values; recurrenceRuleSignatures tracks
interval type/size changes for stale-state re-arming. Both are native class B,
not application-specific schedule records. Source hashes/line evidence are private.

Preserve every original value. Do not simulate the engine's reset/trim behavior
in preparation. Scheduled setup can re-arm state; manual triggers bypass filtering.
The emitted scheduled-time dedup key is separate from these arrays and from
application reminder idempotency. Import APIs, restart loading, persistence flushing
and historical compatibility still need integration evidence. Unknown owners,
keys, values/shapes or versions remain unapproved; generic snapshot inventory is C.
See [native-state review](native-scheduler-state.md) for source-scope details.

## D06 — Do not equate static review with executable safety

Accepted. Seven Code v2 bodies were inspected without execution. The computed-member
indicator resolved to returned array literals; it was not a credential/eval operation.
That finding does not clear all Code. Code acceptance/conversion remains a separate
review decision. Native-state recognition also does not grant a reset/import policy.
Two current structural candidates pass; the other two are retained losslessly
without bypassing these gates. None is certified n8n-importable or runtime-tested.

## D07 — Isolate integration by construction

Accepted configuration design; execution approval pending. Use only the standalone
2C Compose file, explicit test project, internal network and test databases. No
ports, production mounts, .env inheritance, Docker socket, real bot or Code workflow.
Images must be verified local IDs; no pulls or mutable-tag fallback. Generate new
test credentials in the process session. Bind only individual synthetic fixture
files read-only. Mocks make no outbound calls and retain no payloads.

Runtime data is tmpfs and will be lost on teardown or PostgreSQL restart. Test
n8n-only restarts with PostgreSQL alive to investigate persistence. Approval for
startup does not implicitly approve imports/activation; request a clear combined
scope or stop at a narrower granted boundary. Do not merge test and production
Compose. Runtime compatibility, bootstrap and health are not established offline.

## D08 — Keep application and n8n migrations separate

Accepted strategy, not an installed runner. Historical m2a SQL is not the live
baseline. Adopt an immutable reviewed application baseline for empty test/dev
DBs, then versioned/checksummed migrations with target checks and locking. Existing
production must not replay baseline/seeds. n8n manages its own metadata migrations.
No production ledger, migration, restore or schema adoption was performed here.

## D09 — Preserve working-tree work and task-specific holds

Accepted. Git HEAD 62e96e6 records 2A. Later source/config/docs may be uncommitted
or untracked; inspect status before work, do not clean/reset them. General policy
permits safe local development-branch commits under the current owner instruction.
Historical holds do not override later explicit scoped approvals; private source
promotion, production access, deployments and merges remain gated. Do not bypass sandbox read-only Git/Docker metadata
by escalation, permission changes or relocating .git. No remotes/push/deployment
without explicit approval. Keep this distinction visible in new-session handoff.

## D10 — Managed series require v2 mutations

Owner approved 2026-11-13. Reject legacy update/remove submissions and approvals
when the target recurrence rule has `managed_by=m2d`; require a fresh managed v2
proposal and explicit approval. Check current ownership at decision time under
the same transaction advisory lock as v2 decisions, including requests created
before conversion and stale event-only snapshots. Force does not bypass policy.
Neither version tags nor noncanonical approval strings authorize the legacy
decision entry point to mutate managed state.
Unauthorized decisions must retain the generic authorization response. Return
only the sanitized compatibility reason to an authorized pending requester.

Blocked approval leaves the request pending and all managed state untouched;
the owner can explicitly reject/discard it. Genuine legacy events retain their
existing update/remove behavior. New v2 proposals, approvals, snapshots and
occurrence/series edits retain their checks. Migration 0003 preserves original
legacy bodies verbatim inside guarded blocks, retaining their signatures,
ownership, ACLs, invoker security and configuration; no public bypass alias or
privilege elevation is introduced. A request trigger also guards direct legacy
envelope submission. No historical migration or baseline bytes are rewritten.

## D11 — Lease-checked receipts and read-only reconciliation groundwork

Implemented under the owner's receipt-persistence instruction, 2026-11-13.
Store nullable Telegram chat/message pairs with sent acknowledgement in one
lease-checked transaction. Preserve unknown historical IDs as NULL and the
original four-argument API for old workers. New transport receipts require the
configured destination and a usable positive message ID; acknowledgement failure
never causes a transport replay. Require migration 0004 before gateway ticks.

Inspection is a bounded read-only transaction returning metadata, receipt
presence and a UTC-normalized row-state digest; the digest is not authorization
or proof of non-delivery. [Audited resolution design](RECONCILIATION_DESIGN.md)
was proposed at D11. D12 supersedes only the isolated synthetic resolution hold.
Production resolution and any resend still require separate owner approval; a
resend must be a separate explicit authorization, not a status reset.


## D12 — Synthetic audited confirmed-delivered reconciliation

Owner approved implementation, enablement and testing only in isolated synthetic
PostgreSQL, with invented positive evidence and no Telegram I/O. Implement a
separate operator API using authenticated SESSION_USER name/OID, no request actor
ID, an independently pinned destination, immutable verified evidence and an
approved expiring permit bound to the exact action/observation/reason/operator.
Explicit request confirmation is also mandatory. Default-disable the synthetic
gate and hard-refuse non-test migration/API targets; do not provision production.

Use the common advisory transaction lock, configuration/row locks and fresh UTC
observation versions; recheck permit expiry after a blocking row lock. Persist
only the permitted sent/receipt transition and append-only audit atomically.
Exact action replay reports the prior fact without another write; modified replay
and conflicting receipt/action/delivery identities reject. Preserve attempt,
payload and lease/claim history. Separate NOLOGIN executor and caller roles so
ordinary workers cannot reconcile or edit evidence/audit/permits. Existing worker
leases/acknowledgement and migrations 0001–0004 remain unchanged.

The trusted fixture administrator attests evidence and provisions permits; tests
prove consistency and permissions, not real Telegram receipt authenticity or
protection from a privileged administrator. Real evidence authority/provisioning,
production authentication/roles/TLS and operational enablement need separate
review and authorization. No resend/reset implementation or production gateway
resolution command is authorized. See [design](RECONCILIATION_DESIGN.md) and
[evidence](M2_RECONCILIATION_RESULTS.md). All Milestone 2 including Panchang remains
required before other orchestrators.


## D13 — Panchang Phase 1 design only; implementation decisions pending

Owner authorized Milestone 2F public research, requirements and design on the
existing branch. [M2F_PANCHANG_DESIGN.md](M2F_PANCHANG_DESIGN.md) is a proposal,
not engine/schema adoption or permission to change n8n. Delhi/Asia-Kolkata and
preferred Purnimanta/configurable Amanta are stated requirements. Keep personal
lunar recurrence and festival-specific observance distinct; do not infer every
festival date from a tithi match.

Pending owner decisions: Skyfield/local DE440s recommendation versus licensed
Swiss alternative; exact sunrise/location/ayanamsa; skipped/repeated/Adhika/Kshaya
policies; ritual authority/tradition; stable Hindu identity and multiple advance
notification storage. The one-event/date ledger constraint requires explicit
additive compatibility review, not a hidden reinterpretation. No policy or
architecture proposal in this document is accepted by default.

Stop for approval before implementation. No package/engine, migration, n8n change,
private-file/manifest access, Telegram operation, production capture/adoption,
deployment or merge is authorized. 2B stays blocked; no replacement manifest.
All Milestone 2 including Panchang and operational acceptance precedes other
orchestrators. Production reconciliation and resend/reset remain disabled.


## D14 — Isolated astronomy feasibility; neutral religious profile

Owner authorizes only a standalone offline Skyfield + pinned local DE440s
prototype, not final adoption. Delhi/Asia-Kolkata, Purnimanta default and explicit
Amanta remain; sunrise model/exact Lahiri are hypotheses. Validate intervals,
sunrise classification, physical month boundaries and public reference times;
mark unvalidated month/exception rules unsupported and never guess annual dates.

The owner profile is religiously neutral, superseding D13's pending first-profile
choice. Future supported festivals display named Smarta and Vaishnava dates in
one consolidated reminder when different, with shared dates deduplicated. No
owner sampradaya is assigned. Research the specifically named ISKCON/Gaudiya GCal
11 reference alongside Smarta; do not implement festival rules at this checkpoint.

Preserve cautious exceptional-tithi handling, n8n/PostgreSQL authorization/stable
identity and delivery safeguards. Stop after feasibility; no migrations, persistent
scheduling/reminder integration, private backup/2B search, live Telegram, production,
deployment or merge. See [results](M2F_FEASIBILITY_RESULTS.md) for failed accuracy
gates and unsupported areas. Storage/ritual profiles still need later review.

## D15 — Evidence-bounded lunar-month and annual-preview research

Owner authorizes further isolated multi-year Amanta/Purnimanta research and
experimental anniversary previews only for validated cases, not engine adoption
or general annual scheduling. Keep research APIs separate. Selected Purnimanta
conversion including 2023 Adhika is implemented as a labelled candidate; direct
reference labels and calendar-context inference must remain distinguishable.
An explicit rule/year allowlist bounds previews; unknown or discrepant cases
reject, skipped dates stay withheld, ordinary/Adhika is explicit and no Kshaya
behavior is guessed. Chaitra Shukla anchor year is only a research token, not an
approved regional-era/identity/storage design. See results for evidence limits.
The 60-second accuracy gate is unchanged; old timing failures still block adoption.
Preserve D14 neutral profile, future consolidated named observance design and
all existing architecture/authorization safeguards. Stop at validation checkpoint;
no persistent integration, migration, n8n/Telegram/production/private access,
2B search, festival implementation, deployment or main merge follows.

## D16 — General offline personal lunar recurrence research

Owner authorizes arbitrary-rule annual/monthly research previews beyond D15's
attested example allowlist, not scheduling adoption. Add reusable versioned calendar
identities, canonical ordinary/Adhika backing anchors, explicit instant/sunrise
birth interpretation and repeated-date policy. Skipped/uncertain/Kshaya/unsupported
month cases withhold dates; no automatic fallback. Preserve pinned model and old
60-second timing diagnostics; separately document selected calendar-date acceptance
and its incomplete adoption status. A conservative 300-second date guard and bounded,
profile-scoped caches are research implementation choices, not approved physical
error bounds, persisted schema or final calendar policy. Neutral user profile and
future consolidated named Smarta/Vaishnava observances remain. See preview design.
Stop after offline checkpoint; no DB/n8n/Telegram/production/private access,
backup/2B search, festival implementation, deployment or main merge authorized.

## D17 — All-name reference coverage and provenance-independent research identity

Owner requests completion of selected12-month coverage, explicit direct/inferred
references, logical identity independent of calculation profile and a proposed
calendar-date gate. Research v2 implements separate fixed-cycle logical keys,
provenance and date policy. Profile changes do not create identities automatically;
changed dates are withheld, changed keys/duplicates/legacy mappings require review.
Fixed cycle-count constants are a proposed identity contract, not a phase model.
All12 names are research-enabled after selected evidence; Kshaya/ambiguous cases
remain unsupported. Actual preview300s guard corrected without changing pinned
model or60s diagnostics. Final direct-reference/exception/date/engine approval
and persisted v1 mapping/per-series identity adoption remain owner-gated. No DB
migration, stored reconciliation, production/private access, n8n/Telegram/festival
integration, deployment or merge. See M2F_MONTH_COVERAGE.md for exact limits.

## D18 — Bounded pre-integration assessment, no implicit integration approval

Owner accepts the all-month/v2 checkpoint as offline research and requests a
finite readiness/personal-policy assessment. Pure preview comparison is restricted
to research payloads; application approval/delivery state rejects, changed date or
interpretation/repetition policy requires review even when a calendar key matches.
A calendar key is not an event/series identity or delivery authorization. Existing
astronomy/date evidence is retained without an open-ended timing investigation.
See M2F_PREINTEGRATION_ASSESSMENT.md for classifications and limitations. The
recommended in-memory synthetic contract adapter requires explicit approval and
is NOT implemented. No DB/n8n/Telegram/production/private access, migration,
resend, festival, deployment or merge follows. AGENTS already covers boundaries.

## D19 — Isolated in-memory recurrence integration authorized

Owner authorizes a synthetic offline proposal/approval/ledger adapter for birthday
and wedding series, not real storage, delivery or deployment. Immutable series ID
scopes the existing lunar key; each occurrence/rule snapshot needs explicit owner
approval. Recalculations cannot replace materialized entries or sent/uncertain
history. Opaque in-process owner capability is test authority, not production auth.
The adapter reuses preview validation and DeliveryReceipt and does not implement
SQL conflicts/leases/retries. See M2F_MEMORY_CONTRACT.md for divergences and tests.
Stop after offline checkpoint. PostgreSQL design/execution/migration, n8n/Telegram,
production/private access, deployment and merging remain unapproved.

## D20 — Lunar PostgreSQL design authorized; adoption pending

Owner authorizes repository-only mapping/auth/transaction review and a finite
synthetic acceptance plan, not database execution or implementation. See
[M2F_POSTGRESQL_DESIGN](M2F_POSTGRESQL_DESIGN.md). Recommended one-off projections,
seven metadata tables, trusted session principals, atomic approval, conservative
never-attempted replacement and cancellation tombstones are proposals requiring
approval. The first-test one-at-event reminder limit requires explicit approval
and does not reduce full Milestone2 advance-reminder requirements. No engine
adoption, migrations, private source access, workflow/delivery or deployment.

## D21 — Synthetic lunar PostgreSQL implementation authorized, execution gated

The owner supersedes D20's implementation gate: implement persistence, trusted
owner authorization, atomic approvals, reviewed replacement/cancel, immutable
history and T00–T26 harness autonomously, completing offline checks first. Stop
before PostgreSQL connections or container execution. Branch is
`development/m2f-postgres-integration`; database/production access is not inferred.

Use native Gregorian once projections and the existing worker/ledger. Six tables
are sufficient: combine approved revisions and action audit into one append-only
snapshot log; pending requests remain in schedule_change_requests. Trust separate
login OID/name principals, not caller IDs; all APIs are synthetic-only and disabled
without fixture provisioned principals/profiles. Conservative never-attempted
replacement, immutable key/projection IDs, no restore/resend, and bounded atomic
series cancellation implement the reviewed design. Profile descriptors are
immutable SHA-256-bound JSONB. Existing migration bytes stay unchanged.

One at-event reminder is this isolated acceptance seam; advance/multiple slots
remain required for full Milestone2. Changes to projected identity interpretation
require a future explicit mapping policy and currently reject. No production ACL
rollout, engine adoption, workflow/Telegram activation, deployment or main merge.
See [results and exact pending execution](M2F_POSTGRESQL_RESULTS.md).

## D22 — Isolated lunar PostgreSQL acceptance authorized and completed

Owner explicitly authorizes only the documented disposable PostgreSQL/Docker
lunar acceptance and demonstrated defect fixes, retaining daemon/schema pins,
isolation, SCRAM and cleanup/service-invariance checks. This supersedes D21's
execution gate only for this synthetic cycle. All T00–T26 passed with additive
0007 (calculation command binding) and0008 (fixed search path on the reviewed
baseline recurrence-sync invoker trigger; body preserved). Earlier migration
bytes remain immutable. No authorization/history checks were weakened.

See M2F_POSTGRESQL_RESULTS.md for failure evidence, complete passing cycle and
remaining limits. No production access, live Telegram/n8n tests, astronomical
adoption, deployment, main merge or other orchestrator is authorized.
