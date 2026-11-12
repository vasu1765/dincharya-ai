# Private Code, runtime-state and version review

The non-executing inspector is implemented in workflow_security.py, with a CLI in
review-workflow-security.py. It reads only an explicitly authorized snapshot and
its validated derived private review artifacts. It does not evaluate JavaScript,
start a runtime, call a service, read credentials or fetch database records.

## Evidence and limits

Seven observed Code nodes have version 2 and jsCode-only parameter structures.
Static patterns found no network/HTTP, environment/credential, filesystem/process,
dynamic-import/evaluation, direct database-write, external URL, workflow-state,
logging/timer or obfuscation indicators. All seven reference workflow input;
two reference time/date facilities. Focused investigation resolved the single
flagged node: its three matching occurrences are returned array literals, not
computed-member/property operations. Exact spans, offsets and hashes remain
private, along with every original Code body. Narrow lexical regression tests
distinguish return arrays from input-property patterns, strings, comments, regexes
and property names. The original capability flag is retained; this contextual
explanation does not clear other code or enable conversion. These are indicators,
not a JavaScript AST, semantic audit or proof of absence. Comments/strings can
produce false positives; indirect/obfuscated operations can evade patterns.
Downstream nodes can perform writes or external calls even when Code only returns
transformed data. Code nodes were never executed, including synthetic probes.

A byte-preserving representation is appropriate for private archival review:
original JS strings, Unicode/newlines, node fields, and the full original snapshot
are retained; source digests bind the report to them. This is not security
clearance or an enabled conversion adapter. Code remains rejected by the existing
converter. Importability and execution remain unverified and unapproved.

## Runtime state

The observed nonempty staticData is node-scoped scheduler bookkeeping with two
leaf fields, recurrenceRules and recurrenceRuleSignatures. The initial snapshot-only
review classified both C (unknown). The subsequent verified installed-source
review establishes native class B state for that exact image; see
native-scheduler-state.md. Historical-runtime and import/persistence contracts
remain unverified, and every original value is preserved.
Neither can be classified as disposable/transient from its shape or apparent
contents alone. The owning node type can be linked to Schedule Trigger, but the
snapshot does not establish the runtime implementation's state semantics.

Focused tracing found each key only in staticData, with zero textual references
in workflow node parameters/settings. No application references were found in the
gateway, historical schema or Compose file; repository inspection found review
tool/test/documentation references rather than n8n scheduler implementation.
This does not prove irrelevance: implicit built-in node reads are not visible in
the snapshot. Effects on schedule generation, deduplication, reminder dispatch,
restart and published behavior were unestablished by snapshot-only tracing.
Installed-source evidence now establishes recurrence filtering/re-arming and
native ownership; import API and engine persistence still need isolated tests.

The inspector inventories paths, owner types and shapes privately without
publishing values. It never rewrites state. All original values remain in the
byte-identical private snapshot. Unknown state fails the treatment-approval guard
and conversion still rejects nonempty runtime state. No A/B classifications or
reset/removal approvals are fabricated. Additional unknown state namespaces,
pinData and executionData are inventoried as C and remain blocked.

## Version provenance

All four records contain a current version identifier. Three have no publication
reference in the snapshot; that does not prove historical nonpublication. One
record has active=true and a distinct activeVersionId. Its current node content
cannot be relabelled as the published content. Neither historical versionMetadata
nor the distinct published body is available. The exact current/reference IDs
remain private. Even matching IDs would not prove which version was executing.

Additional specifically approved version-aware export/records are needed to
establish published content. Evidence about running behavior would need its own
approval. No extra records or backup files were accessed to infer these facts.

The final investigation additionally inspected authorized backup filenames and
the plain n8n.dump.contents archive schema inventory, without opening n8n.dump.
TABLE and TABLE DATA entries exist for workflow_entity, workflow_history,
workflow_published_version and workflow_publish_history. These are candidate
sources, not proof of nonempty tables, matching version rows or stored bodies.
The current raw workflow export contains current rows only; no separate published
workflow export was found among the recognized inventory filenames.

Next access request: approve a separate offline, filtered extraction of schema
metadata and only matching workflow/version records from n8n.dump, limited to
workflow_history, workflow_published_version and workflow_publish_history for
the privately preserved IDs. Inspect their definitions before selecting columns;
do not assume publication-reference tables themselves contain node bodies.
Exclude credentials and execution tables; no restore, live access or imports.
Separately approve baseline runtime.txt metadata and review of the exact matching
Schedule Trigger implementation to establish state semantics. Neither access is
performed here. Any state treatment or Code acceptance still needs approval.

## Private artifact contract

The inspector creates a new directory under a mode-700, user-owned private root
outside Git, using existing no-follow/exclusive directory-relative operations.
Files are mode 600: workflow-original.private.json, security-review.private.json,
manifest.json and a REVIEW_ONLY marker. The manifest hashes the original/report;
validation reconstructs the expected report from the same original bytes and
compares every artifact. Flags remain false for execution, state changes, source
promotion, conversion and import compatibility. This is unsigned integrity
evidence, not authentication or a full recovery backup. /tmp is temporary;
permissions do not encrypt data or protect against host administrators/disk access.

After exact-file authorization, use the following placeholders:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/review-workflow-security.py \
  --snapshot /authorized/path/workflows-current.raw.json \
  --prior-review /authorized/private/workflow-review \
  --prior-root /authorized/private \
  --private-root /new/existing-private-mode700-root \
  --output /new/existing-private-mode700-root/new-security-review
```

Only fixed summaries/counts are printed. Detailed node identities, source hashes,
state paths and version IDs remain private. No executable source is printed.

## Test evidence and stop boundary

89 offline synthetic tests pass, covering UTF-8/newline preservation, versioned
Code structure rejection, capability indicators without execution, runtime-state
classification and rejection, distinct version IDs, equal-reference limitations,
private provenance, and rehashed report tampering. Python/embedded Python/Bash
syntax and changed-source scans are also required before completion.

Stop before deciding to accept executable Code as convertible, remove/reset state,
or substitute published content. Required decisions: executable-content acceptance
policy; owner-version evidence for state treatment; approval for exact additional
published-version records. The computed-member false positive is explained, not
used as blanket security clearance.
No source promotion, staging, commit, Docker, production or deployment is included.
