# Phase A status

Phase 2A implements private-only offline source preparation, exact SQL-byte
preservation, conservative content/structure checks, version-aware syntactic
workflow allowlists, credential-reference mapping, strict provenance/manifest
validation, safe path operations, and synthetic regression tests.

No real backup/schema/workflow input, .env, credential or encryption key has been
accessed. No Docker, database, import, polling, production migration or deployment
operation is part of this phase. Roadmap and development policy define the next
approval gate: exact Phase 2B inputs, then first isolated Docker testing in 2C.

Preparation does not produce Git-ready or guaranteed importable files. Scanners
are heuristic; SQL is lexically screened, not PostgreSQL-parsed; publication state
is unverified; live LLM/custom nodes need reviewed adapters. All candidates and
provenance remain outside Git, mode 700/600, unencrypted by the tool. Complete
restore, privileges, schema completeness and n8n runtime compatibility remain
untested until separately approved integration work. See ROADMAP.md for evidence.

Validation: 52 offline synthetic tests passed, Python/embedded Python AST checks
and bash -n passed, and explicit safe-source scans passed. The proposed local
staging failed because sandbox .git is read-only (index.lock could not be created).
No files were staged or committed. Source changes remain available for review and
a later local commit from an authorized writable Git session. No remote was used.
