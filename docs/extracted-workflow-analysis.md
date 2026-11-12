# Extracted workflow provenance analysis

analyze-extracted-workflows.py reads only explicit authorized extraction artifacts
and current-snapshot proof, and writes private output outside Git. It never calls
Docker, connects a database, evaluates SQL/Code, imports or promotes a workflow.

The input completion marker and five exact checksum entries must validate. The
authorized list must contain exactly the six approved IDs supplied by the caller,
matching the authorized TABLE/TABLE DATA names in the fresh TOC. Metadata and SQL
are read once per verification/analysis step. No other extraction log/data file
is traversed or opened. The archive hash is preserved from the administrator's
provenance rather than re-opening the original archive in this analysis phase.
Hashes are unsigned evidence, not authentication against a wholly replaced set.

## Offline COPY parser and schema mapping

extracted_workflows.py parses only public.workflow_history,
public.workflow_published_version, public.workflow_publish_history. Each must have
one definition and one COPY FROM stdin block with exactly the reviewed column
layout. Other tables, statement types, layouts, duplicate sections, malformed
escapes, row-width errors and unterminated blocks reject. Only standard pg_dump
SET/set_config framing is accepted outside definitions/data. SQL is never executed.
PostgreSQL text escapes, UTF-8, nulls, JSON strings and multiline Code text are
decoded without eval. Original extracted SQL bytes remain unchanged privately.

The explicit mapping uses history workflowId/versionId/nodes/connections and
published-version workflowId/publishedVersionId. Publication-history rows are
historical events only. Versionless activation or deactivation events are retained
privately without inventing IDs, inferring current publication, or reporting a
missing body for a nonexistent reference. Unknown event types reject review.

Historical settings/staticData are absent from this reviewed history layout.
They are not populated from current settings/state. Published bodies are evidence
objects, not complete/importable published-workflow candidates. Exact history row
strings and decoded bodies are preserved privately. Current snapshots remain
separate and retain all original state and version identifiers.

## Comparison and candidate boundaries

Object-key order is ignored for JSON comparisons because the raw jsonb snapshot
can serialize keys differently from history JSON. Array order, scalar types,
Code text and parameter values remain significant. Originals are never rewritten
for comparison. The report distinguishes nodes, connections, changed node fields,
Code bodies and current-to-same-version-history alignment. A canvas-only change
is not presented as proven runtime equivalence. Missing history fields remain
unknown; matching nodes/connections do not establish complete settings or runtime.

Only records accepted by existing structural/security adapters become current
review candidates. Code/runtime-state gates remain in place. Every rejected
original stays in the private snapshot and extracted SQL; no failed record is
silently dropped. All original history/publication rows and event-reference
resolution records remain private, including personal authors/user identifiers.

The private analysis contains exact original SQL/snapshot, parsed tables,
current candidates/provenance, separate published bodies, version resolutions,
rejections, unversioned events and extraction provenance. Its strict manifest
includes digests and false execution/state/promotion/historical-runtime flags.
Validation reconstructs the full expected analysis from original bytes and rejects
altered claims. No report authorizes SQL execution, imports or Code acceptance.

## Administrator-only Schedule source export

The minimal administrator invocation, outside the Codex sandbox, is:

```bash
SCHEDULER_SOURCE_ROOT="$HOME/dincharya-private/phase2b" \
  bash scripts/export-scheduler-source.sh
```

This requires an existing owned mode-700 private root outside Git. The script
selects the local image with the administrator-provided 6723b440354b prefix,
pins its full ID, and checks n8n package version 2.47.3 inside a disposable
network-disabled/read-only container. It overrides n8n's entrypoint with a source
copy shell. No live containers, workflows, volumes or credential files are read.

The bounded source archive includes these exact paths relative to
/usr/local/lib/node_modules/n8n:

- package.json (n8n release metadata)
- node_modules/n8n-nodes-base/package.json (node-package provenance)
- node_modules/n8n-nodes-base/dist/nodes/Schedule/ (including
  ScheduleTrigger.node.js, sibling helper modules and source maps when present)

If that layout/entrypoint is absent the command fails rather than searching
unrelated image paths. We must inspect imports before identifying any required
helper modules outside that bounded directory. No such extra files are copied
automatically. The archive, hashes, image metadata and completion marker remain
mode 600 under a new private mode-700 directory. Never blindly unpack unreviewed
archive paths/symlinks into a repository.

The source export script has syntax, static-boundary and fake-Docker tests; Codex
has not run real Docker. Providing source permits inspection, not state reset or
historical runtime assumptions. Scheduler fields remain class C until source
semantics and relevant provenance are established. A later verified-source review
classifies the two native fields B for that exact image (native-scheduler-state.md),
while the generic snapshot-only inventory remains C. The local 2.47.3 image is not
by itself proof of the runtime that generated historical records.
