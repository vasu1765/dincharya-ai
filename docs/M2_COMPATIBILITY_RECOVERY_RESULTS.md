# Focused 2D/2E evidence — 2026-11-13

Development base: `120b28a`, branch `development/m2-recovery-acceptance`.
Source/migration/tests in this checkpoint remain uncommitted until owner records
them; Git metadata is read-only in the sandbox. PR #1 live acceptance was not repeated.

## Demonstrated defect and approved policy

A synthetic legacy request survived an approved managed occurrence override,
then its event-only snapshot allowed mutation of the managed series. This failed
the boundary assertion before the fix. Owner selected D10: block legacy
update/remove for managed series, retain genuine legacy behavior and require v2.

Migration 0003 guards both original public legacy entry points without changing
their signatures or privileges. Original bodies remain byte-for-byte within
nested guarded blocks; runtime checks compared body substrings and ownership,
ACLs, security mode, function configuration, volatility and parallel properties.
New request triggers reject direct legacy envelopes targeting managed series.
Current-ownership checks share the v2 transaction lock, so pre-conversion pending
requests cannot race conversion. New submissions fail with sanitized SQLSTATE
22023; authorized pending approvals return false with the v2-required reason.

## Results

| Focused check | Result |
| --- | --- |
| legacy_coexistence.sql | PASS: legacy add/update/remove/reject/replay/staleness/authorization, v2 routing/coexistence, low-level v2-envelope rejection, in-flight legacy mutation veto |
| legacy_managed_boundary.sql | PASS: pending update/remove before conversion, override staleness, direct/dispatcher/force rejection, forged version tags/noncanonical approval, unauthorized generic response, blocked fresh official/direct submissions, explicit discard and continued v2 proposal/approval/replay protection |
| legacy-concurrency | PASS: observed two decisions waiting on conversion's advisory lock; both rejected afterward, fresh concurrent submission rejected, original request pending and event enabled |
| reminder_recovery.sql | PASS: inclusive six-hour edge, exclusion one second beyond, exact lease expiry, stale acknowledgement rejection, immutable quarantine/sent history, cancellation/replanning with stable date identity and no old-time claim |
| Adapter offline tests | 8 PASS, including bounded metadata-only quarantine inspection and invalid bounds rejected before connecting |
| Migration renderer offline tests | 4 PASS, including new migration rendering |
| Focused runner offline tests | 3 PASS: missing approval, symlink/unknown/duplicate/misordered cases, wrong daemon rejected before unsafe operations |

Only new/changed SQL cases were executed; no n8n, original concurrency suite,
Telegram or full regression suite was rerun. Initial fixture assumptions about
legacy auto-created rules and legacy snapshot shape were corrected to match the
authorized schema. Startup readiness, psql result parsing and new-wrapper compile
issues were corrected before the passing results. Assertions were not weakened
to accept the demonstrated managed-snapshot bypass.

Every completed runtime attempt verified the pinned local daemon/image, used
fresh disposable PostgreSQL 17, tmpfs-only storage, read-only root and no network,
ports or host mounts. Only the exact previously authorized schema input was read
and remained unchanged. Three migration entries and repeat no-op were verified
in the new-migration run. Each container was removed and original running
container IDs stayed unchanged. A final read-only audit found no disposable
containers left under this task's prefix, including after the interrupted call.

## Limits and next work

`PostgresReminders.list_quarantined` is a bounded read-only adapter building block,
not an operator resolution UI. It returns metadata only, never payload/title,
chat identity, worker token or raw error text, and cannot clear/reset/resend.
Its connection/SQL contract was tested offline; no live operator listing was run.
Receipt persistence and audited resolution actions remain separate P3 work.
Broader adversarial/legacy API paths remain before closing all 2D; outage restart
matrices remain before closing 2E. Panchang policy/reference decisions remain
required before 2F implementation. No production credentials/services, deployment,
merge, raw backup promotion or historical JavaScript Code execution occurred.
