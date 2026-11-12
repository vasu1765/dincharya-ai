# Phase A source synchronization

The tools operate offline on explicitly supplied files. No automatic backup,
Docker, database, credential, or production access occurs. Real input access
requires approval identifying the exact files. Do not pass .env, credential
exports, keys, full database dumps, or unapproved backups.

## Private-only preparation

Preparation creates **unencrypted private review candidates**, never Git-ready
source. A scanner cannot prove absence of opaque secrets, private IDs, personal
text, or executable hazards. --reviewed-inputs attests initial human review, not
permission to publish. No promotion command is implemented. Later source adoption
requires a separate content review and explicit selection of accepted files.

Both candidate and provenance directories must be new, distinct, direct children
of --private-root. The root must already exist, be owned by the current user,
mode 700, and outside Git (including worktrees/bare repositories). Symlink roots,
output directories and payloads are rejected. No-follow directory-relative file
operations and exclusive creation avoid following replacement links or overwriting
files. Files use mode 600. This protects against ordinary accidental path reuse,
not a malicious same-user/host administrator. Unix permissions do not provide
encryption or protection against Windows administrators/physical disk access.

After separate approval to read the supplied files, replace these placeholders:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/source_sync.py \
  --schema /approved/input/application-schema.sql \
  --workflow /approved/input/workflows.json \
  --input-format raw --state unknown --reviewed-inputs \
  --private-root /private/existing-mode700-root \
  --output /private/existing-mode700-root/new-candidate \
  --private-output /private/existing-mode700-root/new-provenance

PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/validate-source.py \
  --bundle /private/existing-mode700-root/new-candidate \
  --private-metadata /private/existing-mode700-root/new-provenance \
  --private-root /private/existing-mode700-root
```

Do not use a repository directory as --output. Existing directories, overlapping
paths, wrong permissions, symlinks, hard-linked payload files, files over 32 MiB,
unknown structure, and unreviewed versions fail closed. Failed writes may leave
private incomplete directories. PREPARED is written last; it is not deployment
approval. Use new output names for a retry; never overwrite an earlier candidate.
Safe error categories identify the problem without echoing raw contents, parser
exceptions, or credential-bearing paths. Do not paste private inputs into logs.

## Workflow contract

Raw PostgreSQL rows are **not guaranteed n8n-importable**. Neither editor nor raw
candidates are semantically validated by n8n. --state defaults to unknown; draft
or published are unverified human declarations. Raw current rows cannot be
labelled published. Editor published declarations need coherent version IDs and
active metadata but still do not prove which version was actually deployed.
Process distinct states/versions in separate bundles.

The adapter currently recognizes only manualTrigger v1 and Set v3.4 structures
covered by synthetic fixtures. This is an intentionally narrow syntactic
allowlist, not runtime compatibility certification. Unknown node types/versions,
fields, settings, branch types, malformed metadata, duplicate IDs/names, and
unsupported Set options/assignment structures reject preparation. The live chat
workflow's LLM nodes will require separately reviewed adapters and synthetic
fixtures; never bypass these checks to ingest an unsupported workflow.

Nonempty pinned/static/execution data, sensitive parameter keys (including apiKey
variants), authentication headers and token patterns are rejected. Credential
references are accepted only as maps of type to exactly nonempty string id/name
pairs; passwords/tokens/extra credential fields are rejected. References are
removed from candidate nodes and preserved in private metadata alongside the
complete original record. The exact original workflow input bytes are retained
privately for provenance. No real credential values should be supplied.

Candidates preserve node IDs, connections, expressions, settings and parameter
literals unchanged, except for removing credential-reference fields and setting
workflow active=false. Workflow-level IDs, version/publication metadata, tags,
and descriptions remain in private provenance. Embedded IDs and personal literals
may remain in candidate parameters/expressions: **everything remains private**.
Nothing is silently substituted or declared safe for Git. Later reviewed adoption
must address environment bindings without breaking expressions or references.
Inactive JSON is not an isolation guarantee for any n8n runtime.

## SQL fidelity and limits

Accepted schema bytes are copied exactly, including functions and triggers.
No normalization, redaction, or partial object extraction occurs. Suspected
secrets, top-level data/role/external connection statements, unknown SQL statement
classes, unsafe psql directives, and unbalanced/truncated lexical framing reject
preparation. pg_dump restrict/unrestrict pairs are supported. Function bodies can
contain INSERT without being mistaken for top-level seed data.

These checks are **lexical safeguards, not PostgreSQL syntax validation**. They
cannot establish complete dumps, safe execution, correct privileges, semantic
validity or absence of secrets. In particular function bodies and allowed DDL
can execute code if later applied. Nothing is executed by preparation. Complete
catalog inventories, function signatures, trigger/extension/security review,
and a build from scratch require separately approved isolated PostgreSQL tests.
A truncated dump ending at a statement boundary can still pass static checks.
Never run an accepted schema in production just because validation passed.

## Validation and provenance

The candidate contains application-schema.sql, workflows.candidate.json,
manifest.json and PREPARED. Provenance contains workflow-input.private.json and
workflow-provenance.private.json. Additional or missing files fail validation.
Every artifact is read once into bytes through no-follow descriptors, with type,
mode/owner, size, link and concurrent-modification checks. Parsing, hashing and
comparison use those bytes; files are not reread for different checks.

The manifest has an exact field/type schema, hashes for schema, workflow input,
candidate workflows and provenance, and a positive integer workflow count.
Required flags: candidate_only=true, human_review_attested=true,
promotion_approved=false, state_verified=false, import_compatibility_verified=false,
database_execution_performed=false. The validator reconstructs candidate content
and private mappings from original input, compares canonical byte representations
(including JSON scalar types),
checks every hash and exact marker content, and rejects private-field injection
or provenance contradictions even when a single artifact's hash is recomputed.

SHA-256 is unsigned integrity evidence, not authentication: an attacker who can
replace all artifacts and the manifest can replace the whole bundle. Host/same-
user concurrent attacks are outside this local offline tool's trust model.
Private provenance is required to validate a candidate. A future Git-source
validator will need its own approved, sanitized provenance contract.

## Later controlled extraction (not authorized by this document)

Prefer the verified existing capture after approval for exact files; do not
repeat production exports unnecessarily. If fresh capture is separately approved,
use the established preflight/identity-checked capture tool from the normal Ubuntu
terminal with a private destination. It checks all four application tables and
all nine scheduling function names before dumps. Exact command after approval:

```bash
cd ~/projects/dincharya-ai
BASELINE_BACKUP_ROOT=/absolute/path/to/existing-private-backup-root \
BASELINE_MIN_FREE_GB=5 bash scripts/capture-baseline.sh
```

This command creates full private database backups as well as schema and current
workflow snapshots. It is not a schema-only shortcut; approval must cover that
scope, Compose reading existing configuration, and production data capture.
Check COMPLETE, capture-status.txt, workflow-export-status.txt and SHA256SUMS
privately. Do not print dumps, resolved Compose config, .env or container
credentials. Prefer this tool over shell snippets that omit identity checks or
silently skip finalization. No capture is run as part of Phase 2A tests.

Portable workflow export needs a separately approved editor download without
saving/publishing changes, recording exact n8n/workflow/version/state evidence.
Do not invoke live CLI initialization or restore the production n8n database
under the current authorization. First isolated Docker tests and any imports
require separate approval and no network access to real Telegram/services.

## Acceptance and adoption boundaries

Run offline tests with synthetic fixtures only:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v
```

Before a local source commit, use check-safe-source.py on explicit non-secret
repository paths, for example:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/check-safe-source.py \
  scripts/source_sync.py scripts/validate-source.py tests/test_source_sync.py
```

The scanner rejects secret/capture paths before opening them and never recursively
reads a repository or prints matching content. It reports input indices only.
Pass every proposed commit file explicitly and review the diff; this heuristic
check does not certify absence of secrets or personal information. Synthetic
detector probes are assembled at test runtime rather than storing complete
credential-like strings in source fixtures. No scanner exemptions are used.

Before later Git adoption, independently review all SQL comments/bodies, URLs,
headers, credential bindings, personal/chat IDs, literals, expressions and node
versions. Record review decisions privately against hashes. Verify source
completeness in isolation, then select only reviewed sanitized source for Git.
Do not stage a candidate directory wholesale. Raw/provenance inputs never enter
Git. Tests, candidate hashes and an attestation do not establish runtime behavior.
Keys, global database roles, n8n filesystem data and recovery rehearsals remain
separate work. No recurrence, Panchang, migration runner or deployment is included.
