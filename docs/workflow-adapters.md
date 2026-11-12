# Observed workflow adapters

These are offline structural adapters, not evidence of n8n import compatibility.
No production, Docker, workflow execution, imports or commits were performed.
Only the previously authorized snapshot and private rejection report were read.

## Field classification and preservation

| Snapshot fields | Candidate treatment |
| --- | --- |
| name, nodes, connections, settings | Retain, subject to explicit structure/type checks. |
| node parameters, expressions, node IDs, webhookId | Preserve unchanged in private candidates. No evaluation or secret substitution. |
| node credentials | Validate id/name references, move to private per-node mapping; preserve original node record. Never accept credential values. |
| workflow id, versionId, activeVersionId, versionMetadata | Preserve privately; do not guess deployed content from current rows. |
| createdAt, updatedAt, versionCounter, triggerCount, parentFolderId, sourceWorkflowId | Recognize storage/provenance metadata, retain original privately, omit from candidate envelope. |
| meta.templateCredsSetupCompleted | Validate boolean UI/setup metadata; original remains private. Other meta keys reject. |
| nodeGroups | Only empty/null recognized; nonempty groups reject pending presentation/identity mapping review. |
| staticData, pinData, execution data | Nonempty runtime/pinned/execution state remains blocked; never silently strip it. |
| active | Preserve original privately; candidate is inactive and publication state remains unknown. |

Some database fields may also appear in version-specific editor exports. This is
an explicit private-candidate contract, not a claim that this classification is
the portable schema of the installed n8n version. Every original record and input
byte is retained privately. Unknown fields reject rather than being discarded.
Settings now recognize timezone, executionOrder, binaryMode, callerPolicy,
timeSavedMode and availableInMCP with type checks. No setting implies permission
to expose, activate, import or execute a candidate.

## Versioned node structures

- Manual Trigger 1; Set 3.4/3.5 (known assignment structures only).
- PostgreSQL 2.8 (executeQuery, query, empty options or queryReplacement string).
- Schedule Trigger 1.4 (minutes-interval representation).
- Telegram 1.2 (chatId/text, empty additionalFields).
- LLM Chain 1.9 (text/promptType, empty batching, optional messageValues).
- Ollama Chat Model 1 (model, empty options).
- Webhook 2.2 and Respond to Webhook 1.5 (observed fields, empty options).
- If 2.4 and Switch 3.5 (explicit rule/condition/operator structures).

Unknown versions/options reject. Main branches are bounded per node, including
two If outputs and Switch rules plus fallback. ai_languageModel edges are accepted
only from Ollama Chat Model to LLM Chain, with matching type and input index zero.
Synthetic fixtures match field/type shapes, never production parameter values.

Code v2 is recognized as an explicit **EXECUTABLE_NODE_REQUIRES_REVIEW** blocker,
not accepted. Allowing arbitrary executable content or removing runtime state
requires a security-sensitive decision. Do not weaken existing secret checks.
Regex scanning is heuristic; candidate literals and all credential mappings stay
private. Node/API settings and executable expressions are not semantically tested.

## Partial workflow-only review bundles

After exact-input authorization, the new workflow-only path can preserve rejected
records while preparing independent supported records. It checks the snapshot
hash against the exact source-path entry in the previously verified private
integrity report; it does not read other backup artifacts. This reuses prior
manifest verification and is not independent authentication of that report.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/prepare-workflows.py \
  --snapshot /authorized/path/workflows-current.raw.json \
  --integrity-report /authorized/private/provenance/verification.private.json \
  --private-root /existing/private-mode700-root \
  --output /existing/private-mode700-root/new-workflow-review

PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/prepare-workflows.py \
  --validate-only --private-root /existing/private-mode700-root \
  --output /existing/private-mode700-root/new-workflow-review
```

The private bundle contains the complete original workflow input and integrity
report, converted candidates, original-index provenance and credential mappings,
rejection categories, a hash manifest and REVIEW_ONLY marker. Validation reads
each file once and reconstructs the full expected bundle, including rejections
and required false approval/publication/execution flags. Missing/extra files,
tampering, changed rejections, or partial writes fail validation. Directory/file
permissions are 700/600; no-follow/exclusive path protections are reused.

The tool does not fabricate the human-review attestation required by the older
combined schema/workflow path. The workflow-only manifest explicitly records
human_review_attested=false. Partial success is never a full source-sync result.
No source promotion is performed. /tmp output is temporary and unencrypted;
Unix permissions do not protect against Windows administrators or disk access.

## Current result and next decision

Across four authorized records, two convert and two reject: runtime state and
executable Code respectively. The active current row's version differs from its
activeVersionId; raw data cannot establish the published content. Full published
version verification requires separately approved version-aware export/testing.
66 offline tests pass; no n8n importability or runtime correctness is claimed.

Before further conversion, decide how executable code will receive a private
security review and how required runtime state should be preserved or deliberately
excluded with explicit behavioral acceptance. Source promotion and first isolated
Docker/import tests remain separately gated. No further backup access is implied.
