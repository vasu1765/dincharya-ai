# Milestone 2E synthetic reconciliation evidence

Checkpoint: `development/m2-recovery-acceptance`, base `d987b69`. Existing
uncommitted implementation was preserved and reviewed after session interruptions.
This report separates retained successful tests from the small review follow-up.
It is not production enablement or a full regression-suite result.

## Retained completed implementation evidence

The previously completed `reconciliation-concurrency` run passed on fresh
PostgreSQL 17 using the pinned local image and daemon. Its sanitized results:

- Five checksummed migrations installed; original legacy bodies/properties and
  acknowledgement body preserved; authorized schema bytes unchanged.
- Actual non-superuser SCRAM logins and incorrect-password rejection; trusted
  session identity, disabled-by-default gate, spoof/role escalation rejection,
  operator/worker separation and denied direct ledger/private-table access.
- Explicit confirmation, permit, destination pin and evidence checks; unapproved,
  expired, unverified, missing/mismatched, stale, actively leased and resolved
  requests rejected without delivery/audit writes.
- Injected AFTER INSERT audit failure rolled back both audit and delivery update.
  Explicit caller rollback left neither write and did not consume the action.
- Exact replay was idempotent; changed replay and duplicate receipt rejected.
  Attempts, payload, claim/retry/lease history and unrelated row fields preserved.
- Concurrent different operator decisions produced one transition/audit; concurrent
  identical actions produced one recorded result and one replay with one audit.
- Restricted worker claim and normal acknowledgement worked; stale replay failed
  and no duplicate claim appeared. Synthetic gate disabled at completion.
- Disposable teardown passed; original running container IDs unchanged.

At that checkpoint, 24 focused offline tests passed across scoped runs: six new
operator API, eleven affected adapter, four migration-renderer and three focused
runner preflight tests. They cover typed input/explicit confirmation, absence of
actor fields, sanitized private representations/errors, one parameterized call,
unknown commit result without automatic retry, read-only bounded inspection and
boolean-selected restricted worker APIs. No full-suite result is claimed.

The earlier SCRAM setup attempt exposed localhost trust overriding the intended
host method. Explicit initdb host SCRAM configuration corrected it; the successful
run above included a wrong-password negative test. A source-safety heuristic
flagged the provisioning SQL template; separating its escaped literal from the
template resolved the finding without changing or disabling the scanner.

## Resume-review fixes and focused verification

Security review found a permit-expiry timing gap after row-lock contention.
0005 now rechecks `clock_timestamp()` against permit expiry after acquiring the
delivery lock. No committed migration was rewritten: 0005 remains uncommitted.

Password provisioning uses SQL stdin and authentication uses inherited
`PGPASSWORD`, with names alone in Docker command arguments. Review additionally
hardened disposable PostgreSQL logging: statement/duration/sampling/parameter
logging disabled and error-statement logging restricted to PANIC. This prevents
ordinary provisioning diagnostics from recording the password-bearing DDL;
trusted host/daemon/DB administrator inspection remains outside this boundary.
Passwords are freshly random, session-only and never written into repository
files or printed. PostgreSQL/Docker raw outputs are not published.

Only `--case reconciliation-review` was executed during this resume review:

- Reverified daemon `44c1ef83-c50e-4ecc-8f19-4b112bc40f29` and pinned local image,
  empty fresh database, five migrations and preserved legacy contracts.
- Checked effective PostgreSQL logging settings; authenticated distinct SCRAM
  sessions and rejected an incorrect password.
- Observed an operator waiting on the locked delivery while its permit was still
  valid; held the lock past expiry. Result was `authorization_invalid`, with the
  complete delivery row unchanged and zero audit entries.
- Disabled the synthetic gate; removed the exact disposable container; original
  running container IDs unchanged.
- Re-ran only affected offline checks: four migration-renderer and three runner
  preflight tests, all passed. The completed reconciliation-concurrency, receipt,
  2C, live Telegram and full integration suites were not repeated.
- Explicit 16-file source-safety scan, whitespace/diff checks and changed-Python
  AST checks passed. GitHub issue #2 was updated with results and remaining gates.

## Security review conclusions and limitations

No caller-controlled SQL identifiers or dynamic resolution SQL exist. Python
resolution values are parameterized; the only migration dynamic GRANT formats a
catalog-derived regclass. SECURITY DEFINER owners cannot log in or grant roles;
PUBLIC access is revoked and qualified objects/fixed search paths prevent caller
schema substitution. Operator identity binds `SESSION_USER` name and OID.
Evidence, destination and explicit permit are independently provisioned private
immutable records. Row/advisory locking, fresh versions, unique identities and
atomic audit/state writes enforce the synthetic action boundary.

Evidence validation proves bindings to a trusted attestation, not independent
Telegram receipt authenticity. No real evidence provisioning, production role/
TLS/operator workflow, privileged-admin tamper resistance or external exactly-once
claim is established. Original worker APIs and migrations 0001–0004 are unchanged;
restricted worker mode is opt-in. Full restart/outage, source adoption, Panchang
and operational acceptance remain open. See [design](RECONCILIATION_DESIGN.md).

Only the exact previously authorized schema file was read, without modification.
All runtime resources were disposable, read-only-root/tmpfs, network-disabled,
without host ports or mounts. No Telegram API call, resend/reset, production
credential/service access, deployment or merge occurred. Git metadata remains
read-only; commit instructions and the exact safe list are in [HANDOFF](HANDOFF.md).
