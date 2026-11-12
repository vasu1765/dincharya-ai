# Verified installed Schedule Trigger state

The authorized source archive was checksum-verified and inspected in memory,
without unpacking files into source, loading modules or executing JavaScript.
Package metadata identifies n8n 2.47.3 and its packaged n8n-nodes-base 2.47.2.
These distinct version numbers are recorded rather than assumed identical.
Findings apply to the exact exported image; they are not proof of every upstream
release or the runtime that produced historical workflow versions.

## Native state ownership and role

ScheduleTrigger.node.js obtains getWorkflowStaticData('node'), initializes
recurrenceRules/recurrenceRuleSignatures when absent, and passes recurrenceRules
to GenericFunctions.recurrenceCheck before emitting scheduled outputs. These are
native n8n scheduler fields, not Dincharya's PostgreSQL recurrence_rules table or
application reminder-delivery bookkeeping.

recurrenceRules holds per-rule last-accepted execution-time values used to gate
recurrence intervals. The helper reads a prior value, allows an eligible interval,
and updates its slot. Null/undefined last-execution values mean no prior run.
If recurrence gating is disabled for a rule, the helper returns without using its
last-run value. This does not make the field universally disposable.

recurrenceRuleSignatures stores per-index interval type/size signatures. Scheduled
trigger setup calls resetStaleRecurrence. Changed signatures re-arm stale slots;
valid pre-signature legacy values may be retained for supported interval types.
Both arrays are trimmed to the current rule count. This is native setup behavior,
not permission for source tooling to emulate a reset or trim real state.

The node separately constructs a deduplication key from workflow ID, node ID and
scheduled timestamp when available. The recurrence arrays are cadence/filtering
state, not that delivery key or an exactly-once Telegram guarantee. Downstream
application idempotency/persistence is outside this node source's evidence.

## Classification and implications

The two recognized arrays, under an observed Schedule Trigger v1.4 node namespace,
are class B: behaviorally significant persistent state for the reviewed image.
Original values stay unchanged. Unknown namespaces/keys, unsupported owner versions
or unverified source evidence remain class C. Neither classification grants reset,
conversion, import, activation, source-promotion or runtime compatibility approval.

- Import: retain original state in private baseline/provenance. Dropping/resetting
  it can change whether a later scheduled tick emits. Import API preservation or
  stripping of state is not established by this source subtree.
- Activation/setup: non-manual setup validates intervals, applies signature-based
  re-arming, then registers cron rules. Activation can therefore update engine
  state; source preparation must not simulate that mutation.
- Manual testing: manual trigger calls bypass the recurrence filter. Setup may
  still initialize missing arrays. Manual success does not verify scheduled cadence.
- Restart: if native trigger setup is invoked with retained state, the helpers
  will read/re-arm it under their documented branches. The engine's restart/load,
  serialization and persistence-flush contract lives outside the exported subtree
  and remains an integration-test question.
- Recurrence: preserved values and signatures may affect interval eligibility.
  Exact historical semantics cannot be inferred solely from the current image.

scheduler_source_evidence.py records source hashes and line anchors for ownership,
filtering, re-arming and separate dedup keys. Anchor checks bind this manually
reviewed profile; they are not a general JavaScript semantic/security verifier.
review-scheduler-source.py writes private source/state evidence and original
snapshot bytes outside Git, mode 700/600. It never modifies the workflow or opens
credentials. Generic conversion gates remain unchanged until a reviewed
native-state-preserving representation contract and Code acceptance are approved.

## Remaining workflow and test boundaries

Two current structural candidates remain validated; the other two are preserved
losslessly in private originals but blocked by native-state/Code acceptance gates.
One referenced published body was located; it differs only by a node position in
the compared nodes/connections. Historical settings/state and actual executing
version remain unverified; no current values were substituted as published ones.

Milestone 2C configuration is prepared in tests/integration with synthetic data,
separate services, internal networking, ephemeral storage, no production mounts,
and mocks. It has not been started or import-tested. Approval must explicitly
cover first isolated startup/teardown, synthetic DB initialization, and any
synthetic workflow imports/executions/activation. No Code nodes or production
workflows are part of that proposed approval. Production and source promotion
remain separately gated.
