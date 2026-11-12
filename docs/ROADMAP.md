# Dincharya AI roadmap

Milestone 2 must finish before Milestone 3. Roadmap entries describe intent, not
authorization to cross an approval gate.

| Phase | Scope | Status / exit criteria |
| --- | --- | --- |
| 2A | Harden offline source preparation, validation, secret handling, tests | Offline acceptance complete: private-only candidates, strict provenance/manifest checks, 52 synthetic tests. Local staging/commit blocked by sandbox read-only .git. No real inputs accessed. |
| 2B | Synchronize reviewed PostgreSQL and n8n source | Blocked on approval for exact input files. Verify provenance, review literals, preserve SQL bytes and workflow metadata, adopt reviewed source. |
| 2C | Isolated integration tests | Requires first-time Docker test approval. Reproduce schema, verify workflow compatibility, mock external services, no production mounts/credentials. |
| 2D | Advanced Gregorian recurrence | Add/edit/remove, series/occurrence scope, proposals and approvals; depends on 2B/2C. |
| 2E | Occurrence-based reminders | Idempotent delivery, retry/outage/concurrency tests; depends on stable occurrence semantics. |
| 2F | Delhi Hindu Panchang | Agreed calculation/source/tradition and Delhi location; Ekadashi, festivals, Hindu recurrence; verified reference dates. |
| 2G | Integration and controlled deployment preparation | Full regression/restore rehearsal, reviewed migrations/workflow diffs, recovery plan; production deployment separately approved. |

Current source is an early prototype; historical m2a scripts are not the live
baseline. Live schema/workflows are not yet reviewed source. Baseline capture was
reported successful, but real inputs have not been processed by these tools.

After Milestone 2: Adhyayan (spiritual/career learning), Arogya (fitness/vegetarian
nutrition), Atma-Chintan (accountability/reflection), Vittiya (recurring invoices
and approvals), then India VPS deployment and operational hardening. Paid services
and deployment always require approval.

Milestone 2A acceptance:

- [x] Private-only candidates; no automatic public/Git promotion.
- [x] Known sensitive content and unsupported structures fail closed with safe errors.
- [x] SQL bytes faithful; lexical safety/completeness limits explicit.
- [x] Workflow references/provenance preserved; declared review/state remains unverified.
- [x] Strict single-read bundle validation and tamper/partial-write tests.
- [x] Safe first-run instructions and path/permission checks.
- [x] 52 offline regressions pass; static/explicit source secret checks pass.
- [x] Safe staging attempted after checks; Git could not create index.lock because .git is read-only in the sandbox. No commit created; complete from an authorized writable Git session.

Evidence command: `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests`.
Also AST-parse scripts/tests and capture embedded Python; `bash -n` capture script;
run check-safe-source.py on explicit non-secret source paths, then review Git diff.
These are offline checks, not SQL execution, n8n import, or recovery evidence.
