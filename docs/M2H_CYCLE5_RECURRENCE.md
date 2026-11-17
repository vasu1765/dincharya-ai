# M2H Cycle 5 — Recurrence and notification policies

## Isolated development

A new annual lunar rule defaults to automatic. The authenticated owner reviews
the rule once, including the month, paksha, tithi, Amanta/Purnimanta, ordinary or
Adhika identity, repeat policy, civil time and notification offsets. The worker
scans up to 400 days ahead and revisits future candidates on startup and every
five minutes. It records withheld years and never selects an ambiguous, skipped,
unsupported or sunrise-sensitive date. It uses the existing Drik Delhi and IMD
PAC policy, 90-second publisher diagnostic and 300-second sunrise guard.

Existing annual rules retain manual per-year review and their original at-start
delivery policy. To bring one under Cycle 5 management, use
`/recurring_adopt SERIES manual` or explicitly review
`/recurring_adopt SERIES automatic`. `/recurring_change ID manual` and
`/recurring_change ID automatic` change the mode of a managed lunar rule.

Gregorian one-off, daily, weekday and annual activities use the existing civil
occurrence generator. Leap-day rules occur only in leap years. The generator
evaluates bounded ranges on demand. Lunar projections, schedule writes and policy
activation use one database transaction after the independent guarded calculation
is recorded. Gregorian modifications retain event IDs and occurrence overrides.
Lunar replacements cancel the prior series and preserve its history. If a future
lunar appointment already reached the send boundary, the replacement is withheld.
Lifecycle changes require an authenticated review with a snapshot and revision.

### Telegram examples

The trailing clauses of a new rule use semicolons. A bare routine defaults to
`none`. An explicit lunar reminder request without offsets uses `at_start`.

```text
Schedule Havan every day at 6:30 AM, but don't remind me.
मुझे Friday study class हर शुक्रवार को १६:३० बजे
Remind me 15 minutes before my Friday study class.
Schedule Appointment on 2027-03-15 at 09:00; one day before and one hour before
Remind me "Family puja" every year for lunar Chaitra Shukla Navami Purnimanta ordinary first in 2027 at 7 AM; automatic; at start
```

Use `/recurring_rules` to read managed rules and withheld years. Use
`/recurring_change ID pause|resume|cancel|notifications|replace` to obtain a new
preview. Notification edits accept `none`, `at start`, positive minute/hour/day
offsets, or a combination. Named notification edits require one exact title.
Commands and confirmation buttons require the configured owner in their private
chat. An expired or restarted preview has to be reopened. Approved revisions,
withheld-year records and delivery claims are durable.

## Delivery and recovery

The four policies are `none`, `at_start`, `before_start` and
`before_and_at_start`. The worker supports up to nine distinct slots, with
advance offsets bounded at seven days. The additive ledger keys slots by
event, occurrence date and offset. Previously approved activities stay on the
legacy queue unless explicitly brought under the new policy. Historical sent and
uncertain deliveries remain terminal. Slots that were already due when a new
policy or projection took effect remain absent. A previously eligible slot can
catch up within six hours. The worker uses expiring leases, bounded backoff for
definite rejection and quarantine for ambiguous acceptance or an expired lease.

The gateway reserves a withheld-year alert durably before using its SDK. A
gateway interruption can suppress that alert. The reason remains visible in
`/recurring_rules` and an uncertain alert is never retried automatically.
Live reminder slots and automatic lunar scheduling remain disabled. The new
worker API is exercised on disposable PostgreSQL under the existing restricted
worker role and the SDK path uses simulated Telegram IO.

## Reproduce

Use the pinned dependencies and verified public ephemeris described in
[Cycle 2](M2H_CYCLE2_TELEGRAM.md) and [Cycle 4](M2H_CYCLE4_OPERATIONS.md).
Pass the actual isolated executable paths and a future Chaitra fixture year.

```bash
python -B -m unittest discover -s tests
DINCHARYA_PUBLIC_DE440S=/path/to/verified/de440s.bsp python -B -m unittest discover -s tests/panchang -p test_guarded_calendar.py
python -B tests/integration/m2h_cycle5.py --pg-bin /path/to/postgresql/17/bin --pg-share /path/to/postgresql/17/share --ephemeris /path/to/verified/de440s.bsp --n8n /path/to/n8n --year 2027
```

The runner creates a synthetic PostgreSQL 17 schema, imports the repository
relay into disposable n8n and uses the real Telegram SDK with a mock transport.
It checks migration reapplication, signed requests, owner decisions, restarts,
withholding and alert deduplication, slot identity, policy and lifecycle edits,
outage recovery and a same-cluster restore. Cycle 4's exact authorized WSL
schema acceptance remains recorded at `ac3f29f`. A future compatibility run
must cover the new additive migrations on that schema before promotion.

Run evidence on 17 November 2026. The offline suite reported 306 tests,
305 passed and one optional test skipped. All six pinned-ephemeris guard
regressions passed separately, including the June 30 sunrise disagreement, the
May 1 publication boundary, contradictory Delhi observations, skipped and
repeated tithis, Kshaya and Adhika. The disposable PostgreSQL 17.12 and n8n
2.47.3 run passed with exit 0 and cleaned up its services. It verified a missed
one-day-before slot stays absent, while the same offset for the next occurrence
can deliver independently. The two new migration definitions reinstalled
idempotently. Same-cluster restore preserved control, approval, withholding,
notification and historical delivery rows. Explicit source checks passed.

## Milestone 2 completion matrix

| Area | Evidence | Remaining acceptance |
| --- | --- | --- |
| 2B source provenance | Repository records reviewed. Existing source and manifest evidence preserved. | Supply the exact original manifest path and authorize a read of that file alone, or approve a new reviewed source-adoption route. Any referenced input requires its own scope. |
| 2C scheduling foundation | Prior synthetic foundation acceptance. | Preserve during promotion. |
| 2D–2E civil scheduling and delivery | Civil recurrence plus additive per-offset worker exercised against a disposable database. Prior receipt, retry and quarantine paths retained. | Exact-schema compatibility for new migrations, supervised recovery, wider operational validation and cross-cluster restore. |
| 2F–2G approvals and application | Owner authorization, SDK with simulated Telegram, native relay, migration ledger and restart evidence. | Review isolated results and retain Cycle 4 exact-schema evidence. Any real Telegram acceptance needs separate authorization. |
| 2H lunar calendar | Guarded annual projection, owner-managed modes and withholding. | Broader calendar validation and explicit release approval before any live scheduling or delivery. |

Prior Cycle 4 supplementary unit results and the shared integration runner's
pre-existing source-scanner rejection remain recorded in the Cycle 4 report.
