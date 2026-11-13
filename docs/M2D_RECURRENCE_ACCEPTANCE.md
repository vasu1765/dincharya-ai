# Milestone 2D recurrence API acceptance

Branch `development/m2-recovery-acceptance`; clean entry at pushed checkpoint
`ff6198d83098343128f14b513abf2a9b05d92235`. Local HEAD and origin tracking ref
matched; GitHub confirmed the commit. No open PR was found for this branch.
Issue #2 was updated to record the pushed restart/outage checkpoint.

## Newly verified SQL/API cases

All fixtures are invented. They call `propose_gregorian_change`, the public
`dispatch_schedule_decision` approval path and `generate_event_occurrences`.
Calendar expected dates are literal independent fixtures, not computed with the
predicate under test. No recurrence-predicate-only result is used for these cases.

| Case | Passed result |
| --- | --- |
| Weekly interval across ISO/year boundary | Every two ISO weeks, Monday/Wednesday, 2032-12-29 through 2033-01-26: Dec 29, Jan 10/12/24/26. Inclusive start/end and skipped intervening weeks. |
| Yearly interval and combined selectors | Every two years, months January/December and days 1/31, 2031-12-31 through 2035-01-31: selected-year Cartesian combinations, intervening years skipped, inclusive final Jan 31. |
| Monthly interval and invalid calendar combinations | Every two months, days 29/30/31, Dec 2031 through Apr 2032: Dec 30/31, leap Feb 29, Apr 29/30; no Feb 30/31 or Apr 31 and no pre-start Dec 29. Invalid combinations are skipped, not clamped. |
| Yearly leap selectors | Annual February 28/29 from 2031 through 2033 includes Feb 29 only in 2032, retaining ordinary Feb 28 dates and inclusive bounds. |
| Gregorian century | Every four years from 2096-02-29 through 2104-02-29 skips non-leap 2100 and emits 2096/2104. |
| Until exclusion | Every calendar fixture expands through a full additional 366 days beyond its until date and still matches the exact bounded expected list. |
| Invalid concrete inputs | Non-leap Feb 29, Feb 30, impossible until date, until before start, mixed valid/out-of-range months and month-days reject the entire proposal without persisting a request. |
| Approval and identity | Calendar proposals leave event count unchanged while pending; approval creates the event used for occurrence queries; approval replay rejects. |
| Series changes over existing state | Approved daily series, future ledger rows, approved occurrence exception and cancellation, sent-with-receipt and uncertain history all pre-exist a daily-to-every-two-days rule change. Event/rule and all existing ledger identities remain stable. |
| Conflict/stale decisions | Another approved event conflicts at the new series time. Unauthorized forced approval and ordinary conflicting approval reject; schedule/rule/overrides remain unchanged and request pending. Explicit owner force approves. A parallel old-snapshot proposal still rejects even with force. |
| Overrides and unaffected dates | Existing exception remains byte-equivalent in generated output; stored overrides/cancellation remain unchanged. Removed future dates cancel; retained dates replan. Returning to daily restores ordinary unattempted future work with the same identity but does not erase an explicit cancellation. |
| Historical delivery preservation | Full JSON records for sent-with-receipt and uncertain history remain equal through rule removal/reintroduction and reminder refresh; no attempt/token/history reset, backfill or resend. |

Both new cases passed in one fresh disposable run. Only the calendar fixture was
then strengthened to include beyond-until exclusion and authentication/worker
boundary assertions; that changed case alone was rerun and passed. The series
case was not repeated. Three affected offline runner preflight tests passed.
No application defect was demonstrated and no corrective migration was needed.
All existing migrations and application/worker/role code remain unchanged.

## Security and scope

The existing runner reverified daemon `44c1ef83-c50e-4ecc-8f19-4b112bc40f29` and
pinned local PostgreSQL 17 image before container creation. It applied five
migrations to a fresh empty database and checked preserved legacy bodies/properties
and acknowledgement body. Only the exact authorized schema file was read, unchanged;
no neighboring artifact or private directory was accessed.

Read-only root, tmpfs-only storage, network none and no ports/host mounts were
verified. Host HBA rules require SCRAM; trust rules remain confined to local Unix
sockets inside the disposable container. The calendar fixture asserts those rules,
no direct worker ledger UPDATE privilege/operator membership, disabled resolution
gate and empty audit. Existing NOLOGIN executors, least-privilege caller roles,
immutable audit triggers and safe statement/error/duration/parameter logging are
unchanged. These SQL/API fixtures use the container-local synthetic administrator;
they do not claim a new authenticated end-user or operator acceptance run.
Session-only bootstrap credentials remain environment-only by name, with no
credential values in arguments, repository files or printed logs.

Each run removed its disposable container and verified original running container
IDs unchanged. Both SQL scripts roll back all fixtures. Explicit safe-source,
changed Python AST and whitespace/diff checks passed. No 2C/2E/reconciliation/n8n/
live Telegram suite was rerun; the new series fixture uses reminder APIs only to
check effects of its newly tested series changes. No production access, Telegram
send, resend/reset, deployment or merge occurred.

## 2D acceptance matrix

| Exit area | Status | Evidence / boundary |
| --- | --- | --- |
| Public Gregorian weekly/monthly/yearly intervals, selectors, date bounds, year/leap transitions | Passed for the explicit fixture matrix | New calendar fixture plus retained gregorian.sql; no exhaustive all-calendar-date claim. |
| Series/occurrence separation, approved edits, stable identities and sent/uncertain history | Passed for the requested combinations | New series fixture plus retained initial Gregorian/recovery cases. |
| Mandatory approval/requester checks, malformed input, stale full snapshots, rollback and replay | Passed in covered synthetic API cases | New cases and retained gregorian_adversarial.sql. |
| Concurrent conflict/update/approve-reject/authorization decisions | Passed, retained | adversarial-concurrency; not rerun because implementation was unchanged. |
| Legacy/managed coexistence and pre-conversion/new-request boundaries | Passed, retained | D10/0003 compatibility and legacy-concurrency evidence; managed changes require fresh v2 proposals. |
| Conflict scope and calendar model | Design limitations | Asia/Kolkata Gregorian schedules; default 730-day/maximum 3660-day conflict review and bounded occurrence queries. No infinite-series conflict guarantee or overnight events. Overrides are stored by original occurrence date and apply only when the current rule emits that date; explicit cancellations survive rule edits. |
| Trusted owner identity and managed-v2 application/workflow adoption | Blocked by 2B source/workflow adoption | SQL requester checks do not authenticate an application caller. Missing original provenance manifest and reviewed workflow/schema adoption prevent claiming complete deployed integration or clean reconstruction. Original Code/state remains unexecuted/uncleared. |
| Production/operational readiness | Separately gated | No production migration, workflow promotion, deployment or merge. 2G supervision/restore/clock procedures and all Hindu Panchang scope remain. |

The requested outstanding 2D **synthetic database/API acceptance** is satisfied.
Full 2D integration closure remains blocked by reviewed 2B source/workflow adoption;
all Milestone 2 must still finish before another orchestrator.

## Smallest next 2B action

Obtain the exact original review/provenance manifest path from the owner and
explicit authorization to read that file alone. The owner confirmed the path is
not yet known and did not authorize private searches, unknown backup files or
referenced artifacts. Provenance is blocked; no private search or manifest read
was performed. Do not recreate or substitute a manifest without approval. Do not infer
that the already approved schema path authorizes adjacent files.

After authorization, inspect only the named regular file with no-follow and
restricted-owner/permission checks; identify its format, source/version/hash
bindings and missing evidence. Do not follow its referenced paths automatically.
The named schema may be compared within its existing read-only authorization;
every additional private input needs its own exact path and approval. Keep private
identities/records out of Git and report only sanitized gaps. If the original
manifest is unavailable, obtain an explicit owner decision on reconstructing
provenance from individually approved artifacts; never invent original provenance,
substitute historical settings/state or start fresh production exports by default.


## 2B work available with repository-owned files only

These are next-task options, not additional completed tests or adoption approval:

- Map existing validator contracts from scripts/source_sync.py and
  docs/source-synchronization.md. The code distinguishes format-1 snapshot review
  (REVIEW_ONLY, file hashes and unknown state) from format-2 prepared bundles
  (PREPARED, exact flags and separate private provenance). The missing original
  manifest's format is unknown; do not force it into either format or generate
  a replacement to satisfy a validator.
- Review tests/test_source_sync.py and synthetic fixture coverage for no-follow
  reads, exact file/field sets, hash mismatches, version/current/published
  separation and safe error categories. Any demonstrated tooling defect can be
  reproduced/fixed with invented temporary inputs; no new private access is needed.
  This unrelated suite was not rerun during the recurrence checkpoint.
- Refine a sanitized source-adoption checklist from database/baseline/README.md,
  workflows/README.md and the existing source-sync runbook: identify required
  evidence, review/approval gates and what is absent. Those repository directories
  explicitly contain guidance, not adopted production sources. A checklist is
  not a provenance manifest, private-source adoption or evidence reconstruction.

Work requiring the original private manifest, its referenced files, fresh capture,
source adoption, Code execution or real workflow import remains blocked/gated.
No such work began. Stop at this ready-to-commit 2D checkpoint as the owner asked.
