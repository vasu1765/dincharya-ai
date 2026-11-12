# Offline version evidence contract

version_evidence.py contains pure, synthetic-tested evidence logic. It never opens
archives, starts pg_restore, connects to a database, restores SQL, fetches a
workflow, or changes state. Real table definitions and an explicit schema mapping
must be reviewed before supplying actual normalized rows. No mapping to installed
n8n table columns is assumed or implemented.

## Selective extraction prerequisites

A separately authorized extraction needs an existing compatible local pg_restore
client. Missing tools must not be installed or replaced with a custom archive
parser without approval. First verify a regular non-symlink archive and its exact
checksum entry, then obtain a fresh `pg_restore --list` from that archive. A
cached TOC is not equivalent to executing that command against verified input.

plan_authorized_toc accepts only the exact workflow_history,
workflow_published_version and workflow_publish_history TABLE/TABLE DATA entries
in public. All six entries must exist uniquely. Other schemas, missing entries
and duplicate identifiers fail closed. It excludes credential/execution tables,
ACLs, constraints, comments and dependencies. The function is a plan, not an
extractor. It cannot claim pg_restore filtering has been integration-tested.

Before implementing extraction, verify the installed utility's use-list behavior.
Only selected entry IDs may be placed in a private TOC list. Output must be an
exclusive private SQL file with no --dbname, --create, --clean, restore, SQL
execution or connection option. Review emitted object/table boundaries privately
before parsing rows. Never log data or derive selection from wildcard table
names. If selectivity cannot be guaranteed, stop without extracting anything.
Separate approval is needed to install a client or introduce an execution
environment. Docker access is not implied by backup-extraction authorization.

## Normalized row resolver

resolve_versions takes a current snapshot record, normalized history bodies and
publication references plus archive/snapshot digests. Its internal schema uses
workflow_id/version_id/content and source_table/role; these are not assumptions
about n8n's column names. Roles must be explicitly established from approved
table definitions/records; an arbitrary historical event is never promoted to a
current publication reference based on timestamp or position.

The resolver rejects conflicting current references, snapshot/reference conflicts,
ambiguous duplicate bodies, incomplete normalized bodies and unapproved reference
sources. Identical duplicate history rows count as one version. Relevant counts
include only the selected workflow. Missing bodies yield unknown comparison,
never equality. Nodes/connections are compared canonically with scalar types
preserved; settings are compared only if available. Equality of available fields
is not equality of a complete portable workflow or evidence of its execution.
No fallback substitutes editor nodes for an absent published body.

All originals, identifiers, normalized evidence, hashes and resolution outputs
are private. version_report_payload and validate_version_report reconstruct
the report from the same originals and reject rehashed claim changes. Unsigned
hashes do not authenticate a wholly replaced evidence bundle. Flags remain false
for executing-version proof, state treatment, promotion and verified production
schema mapping. These are offline evidence checks, not integration validation.

## Runtime/source matching and stop boundaries

An image configuration digest alone is not a verified n8n semantic version or
package/source mapping. Review only approved software/runtime metadata. Do not
inspect environment variables or retrieve production container files. An upstream
Schedule Trigger implementation is evidence for the installed behavior only
after its version/build provenance is established. Otherwise retain class C and
all original state. Do not silently substitute the latest upstream implementation.

Actual investigation findings, hashes, software metadata and any selected table
rows remain in private artifacts outside Git. This document describes only tool
contracts and authorization boundaries. No install, extraction, runtime source
acceptance, import, publication, state reset or deployment is authorized by it.
