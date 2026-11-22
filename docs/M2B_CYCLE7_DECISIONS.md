# Milestone 2B artifact decisions — Cycle 7

This review is bound to the Cycle 6 inventory SHA-256 `4f30e69fe7ea74fd128d650aac939bd4159c407d764068b229e989c0aa2552bd`.
Existing repository fixtures continue to be used only for disposable development.
The table proposes dispositions. It does not record an owner decision or authorize
promotion into an authoritative or production baseline.

| Artifact | Source status | SHA-256 | Proposed disposition | Review evidence | Owner decision for promotion |
| --- | --- | --- | --- | --- | --- |
| `database/migrations/0001_gregorian_occurrences.sql` | Current repository database migration | `e4e8f07c4f3233b2f94a01a8f8551693c04624ca95c5d1e3aa029320d075cbb9` | Keep for isolated development | Migration ledger, digest verification and transactional reapplication | Required to adopt authenticated application baseline |
| `database/migrations/0002_occurrence_reminders.sql` | Current repository database migration | `5792db4447c093a8a47142bd7a1dc3da966eedf903e0375cbd5b8523e2e6983f` | Keep for isolated development | Migration ledger, digest verification and transactional reapplication | Required to adopt authenticated application baseline |
| `database/migrations/0003_managed_legacy_boundary.sql` | Current repository database migration | `f5418bd4d944bba240883b36c19d860fd19ecb389f0d93ba7ecdd6a3d68858db` | Keep for isolated development | Migration ledger, digest verification and transactional reapplication | Required to adopt authenticated application baseline |
| `database/migrations/0004_telegram_receipts.sql` | Current repository database migration | `3e50ecdfe91058e771d176826954c7c66889c0bfc38ac902cae158640e0f468f` | Keep for isolated development | Migration ledger, digest verification and transactional reapplication | Required to adopt authenticated application baseline |
| `database/migrations/0005_synthetic_reconciliation.sql` | Current repository database migration | `629fa13920c4c30d4374ff73440ae02aaea312ac4dd628eec166e5555d9dd450` | Keep for isolated development | Migration ledger, digest verification and transactional reapplication | Required to adopt authenticated application baseline |
| `database/migrations/0006_synthetic_lunar_approval.sql` | Current repository database migration | `c1f911aa1c0e0a02338121c0f6c70b64a6993ccb883d1d3e51636b608520b78c` | Keep for isolated development | Migration ledger, digest verification and transactional reapplication | Required to adopt authenticated application baseline |
| `database/migrations/0007_lunar_calculation_binding.sql` | Current repository database migration | `d2663fc16d75fe9e22c84b6e670da1f59e7804050ea24a1320a0aaf4114b5294` | Keep for isolated development | Migration ledger, digest verification and transactional reapplication | Required to adopt authenticated application baseline |
| `database/migrations/0008_lunar_projection_trigger_path.sql` | Current repository database migration | `5d4006db8fbbbeb85bf64296f377537f2dbd8e8f9037ec37ad0a5c1cca81ff21` | Keep for isolated development | Migration ledger, digest verification and transactional reapplication | Required to adopt authenticated application baseline |
| `database/migrations/0009_lunar_delivery_status.sql` | Current repository database migration | `273a9611c584d6d43764d6a993a1df12bde528dc982534cb43c766e8754fde6d` | Keep for isolated development | Migration ledger, digest verification and transactional reapplication | Required to adopt authenticated application baseline |
| `database/migrations/0010_synthetic_annual_lunar_rules.sql` | Current repository database migration | `5f4282a3453818e763855b5f7e10edc2e4757f094214bf97702ba5d0248539ad` | Keep for isolated development | Migration ledger, digest verification and transactional reapplication | Required to adopt authenticated application baseline |
| `database/migrations/0011_synthetic_notification_slots.sql` | Current repository database migration | `bcb72590c3da26ee36c0b6ffca6475f2c572f8d127f3f9c453f220ddaba9ef81` | Keep for isolated development | Migration ledger, digest verification and transactional reapplication | Required to adopt authenticated application baseline |
| `database/migrations/0012_synthetic_recurring_automation.sql` | Current repository database migration | `4619a40af8fdf4a9ead6ceecf2f7abeea94afa741f4fe5a7b045ffc1b09cab0e` | Keep for isolated development | Migration ledger, digest verification and transactional reapplication | Required to adopt authenticated application baseline |
| `database/migrations/0013_synthetic_recurrence_health.sql` | Current repository database migration | `b29ef1c215e3a20c18979fa4e4e7870eb323f11783008d87e73f9b297a62ebc0` | Keep for isolated development | Migration ledger, digest verification and transactional reapplication | Required to adopt authenticated application baseline |
| `dincharya/lunar_service.py` | Current repository security sensitive code | `90996b624d65de5dfda5c40928e17b42f83691642587d8cd0b5c66faa1af7224` | Retain for development | Explicit source scan and scoped signer/review boundary | Required for security-sensitive runtime promotion |
| `prototypes/panchang/requirements.txt` | Current repository application configuration | `90c9fb6e3a9cc6cb06e61cace60819449aa442e63017e6ac9c5a4dccd059d448` | Retain as development source | Pinned repository fixture configuration; used in isolated reconstruction | Required for promotion beyond development |
| `scripts/check-safe-source.py` | Current repository security sensitive code | `c4e22f78a1a829e85f477a250d5cff237b9cfa6930615bd0cb0100f5afda4c38` | Retain for development | Explicit source scan and scoped signer/review boundary | Required for security-sensitive runtime promotion |
| `telegram-gateway/requirements-m2g.txt` | Current repository application configuration | `ad622b3d77d3ad11e2747d966bc860727388bcb2ed7e990788123a4b5d493baf` | Retain as development source | Pinned repository fixture configuration; used in isolated reconstruction | Required for promotion beyond development |
| `tests/integration/compose.json` | Current repository application configuration | `573d75e712fb9cbb399c8a1b5079e1404f7504acb4c3448b0781dbe218aa1c61` | Retain as development source | Pinned repository fixture configuration; used in isolated reconstruction | Required for promotion beyond development |
| `tests/integration/m2h_development_schema.sql` | Current repository database schema | `460f41cb254af06485b5df38b8b6629a9d5adcd25322fd769ecdc3a75b010891` | Retain as synthetic source only | Reconstructed disposable PostgreSQL fixture; separate exact-schema evidence | Required for use as authoritative schema |
| `workflows/m2g-lunar-acceptance.json` | Current repository current workflow | `04414cba56cd0cb1ee543c09d939d214ca544fb4744952d5e42fe37e8654dd0c` | Retain for isolated relay | Inactive Webhook/HTTP Request only; native signed relay and restart passed | Required for publishing or wider runtime adoption |
| `database/migrations/0014_synthetic_restore_fence.sql` | Current Cycle 7 candidate | `75eb1ebebd5f9a932551cdb7b532fe43e4ef99a0115a05b1c105698e0aef7d7d` | Add in isolated development | Append-only audit, stale-review fence and cross-cluster rehearsal. Focused same-database exact-schema acceptance passed | Required for promotion beyond this scope |
| `dincharya/lunar_runtime.py` | Current Cycle 7 candidate | `929ebe8e2d4d585199be472e4ff163c932d7600540549034d701fc587b08c947` | Add in isolated development | Scoped runtime flag and identity before reading restore epoch | Required for promotion beyond this scope |
| `dincharya/lunar_development.py` | Current Cycle 7 candidate | `bd0747bcfb8a852d56ad29892000b4ddda5073a549bb5ee458a41e3cb3dc71cb` | Add in isolated development | Fresh review and epoch-scoped retry identities | Required for promotion beyond this scope |
| `legacy-current` | Current Workflow | Unavailable or excluded | Archive repository evidence; original workflow bodies outside scope | Four current versions recorded in repository evidence | Owner must separately authorize exact inputs |
| `legacy-published` | Published Workflow | Unavailable or excluded | Await review, independent of current definition | Publication identity is distinct from current | Owner must identify and authorize exact published bytes |
| `legacy-history` | Historical Workflow | Unavailable or excluded | Archive provenance records only | 94 versions recorded. Historical bodies are outside this review. | Required before reading or importing history |
| `legacy-code` | Executable Code Node | Unavailable or excluded | Exclude all execution | Seven bodies require separate read and execution authorization | Required for quoting, reading, adopting or executing private Code |
| `legacy-state` | Runtime State | Unavailable or excluded | Exclude | Scheduler state, credentials and volumes are outside reconstruction | Required for any exact private input |
| `original-schema` | Database Schema | Unavailable or excluded | Retain scoped WSL compatibility evidence | Exact Cycle 4 WSL acceptance is scoped and preserved | Authoritative baseline adoption requires review |
| `old-manifest` | Historical Provenance | Unavailable or excluded | Archive existing evidence; unavailable source | Original index unavailable. Existing reports preserved. | No original-path hunt required for the alternate process |

Use [the verification and owner decision procedure](M2B_SOURCE_ADOPTION.md) for the
existing manifest. Record each reviewed disposition in GitHub against its exact
artifact digest. Cycle 7 candidates are separately listed above to preserve the
original manifest bytes and evidence.


## Final acceptance review package

[Cycle 7 exact-schema evidence](https://github.com/vasu1765/dincharya-ai/issues/6#issuecomment-6970326525) confirms migration
0014 on the exact authorized input in the same disposable database. The
cross-cluster synthetic rehearsal is separately scoped. Neither result records
an owner artifact disposition. The inventory digest and every previously
reviewed artifact are preserved.

| Added candidate | SHA-256 | Proposed disposition | Evidence | Further authorization |
| --- | --- | --- | --- | --- |
| `dincharya/private_acceptance.py` | `20ac35b467f1def01e6a7e462352498114a5f5b5473e5c8a18a5b2d9fefcbf93` | Retain as test-only source | Recorded success, stop, quarantine and one-use message budget checks | Separate approval before live execution or source promotion |
| `tests/integration/m2h_private_telegram.py` | `41ae259d4b7665a984abf4724c520929af73cfeff83f202f1455cceeeffe81a7` | Keep in isolated review branch | Dedicated bot and private recipient pin, exact schema preflight, signed native relay and scoped worker | Separate approval before live execution or source promotion |
| `tests/integration/m2h_private_simulated.py` | `4f06c3e08e3bd6970764a8df49420bfcabe6a08797bf2813136c9b6bf574ed9c` | Retain as test-only source | Native PostgreSQL and n8n exercised with simulated Telegram | Separate approval before live execution or source promotion |
| `tests/test_private_acceptance.py` | `ac3b19b72c46eed784460291a8abcea8ec792e21d81dbc95cbdbaeb0818ad0b4` | Retain as a test fixture | Focused replay, receipt, owner and deadline controls | Separate approval before live execution or source promotion |


Record dispositions against the individual digests in the review. The live
test authorization is a separate, revision- and window-bound decision.
Security-sensitive sources, raw backups, private workflow versions and
production artifacts remain outside authoritative adoption.
