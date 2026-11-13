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
