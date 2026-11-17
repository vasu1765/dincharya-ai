# Milestone 2 Cycle 7 release readiness

The branch starts at 29a4484fc4a1951be5e78a5fc1df754979c9434a. The owner
reported exit 0 for the Cycle 6 exact authorized schema, migrations 0011–0013,
native signed n8n, simulated Telegram, recurrence, slots, historical Panchang
and restart. That check is accepted at its original scope.
[WSL evidence in issue #6](https://github.com/vasu1765/dincharya-ai/issues/6#issuecomment-6952877460)

## End-to-end acceptance matrix

The disposable run used PostgreSQL 17.12, the native n8n 2.47.3 relay,
Telegram SDK with simulated IO, signed application APIs, and the actual
reminder worker and SQL slot store. Calendar tests used the pinned DE440s.
The suite validates delivery with controlled fixture clocks. Recovery uses a
second independently provisioned PostgreSQL cluster.

| ID | Journey | Expected | Observed verdict and evidence |
| --- | --- | --- | --- |
| E01 | Daily no reminder | One approved rule, zero slots | **PASS.** Silent SDK rule persisted once. Slot query remained empty. |
| E02 | Daily at start | One eligible slot per occurrence, with receipt | **PASS.** A controlled at-start tick persisted one paired receipt. |
| E03 | Weekly advance | Advance at exactly 15 minutes, no at-start offset | **PASS.** Weekly policy persisted and the advance slot produced a paired receipt. |
| E04 | One-off, multiple offsets | Three distinct slots at 60, 20 and 0 minutes | **PASS.** Receipt on each of the three offsets for the same date. |
| E05 | Annual Gregorian | Eligible next year, stable identity and offsets | **PASS.** Separate receipts for the original and next civil year. Duplicate previews committed one rule. |
| E06 | Automatic annual lunar | Guarded projection, unique after restart | **PASS.** Chaitra fixture projected one occurrence, stayed unique after restart and retained its ID after cancellation. |
| E07 | Historical instant to anniversary | Explicit approval, independent reminder time and sunrise-based date | **PASS.** Preview wrote no appointments. Fresh post-restart approval persisted the calculation. The 1995 fixture's 2027 date was withheld. The approved 2023 fixture projected once. |
| E08 | Read-only historical Panchang | Civil-date and instant answers without writes | **PASS.** English and Hindi SDK responses had no approval buttons or writes. |
| E09 | Modification, pause and cancellation | Authenticated change and durable history | **PASS.** Notification edit preserved sent/uncertain history, pause disabled the event, resume and replacement worked, cancellation stopped future work. |
| E10 | Restart and outage | Relay outage fails closed and recovers cleanly | **PASS.** Native relay forwarded signed traffic after app and n8n restart. Previous in-memory review expired. Competing projector and worker were denied their lock. Health exposed projection and quarantine. |
| E11 | Duplicate and concurrent actions | One approved schedule, no double claim | **PASS.** Duplicate update, button, and independent review retries produced one rule. Parallel SQL worker claims returned distinct slots. |
| E12 | Retry and uncertainty | Definitive rejection retries after backoff, uncertainty stops | **PASS.** At +29 seconds no retry. At +30 after restart, exactly one retry receipt. A separate uncertain attempt entered quarantine and was never sent again. |
| E13 | Cross-cluster restore | Preserve history, fence partial approvals, re-review explicitly | **PASS.** Roles recreated independently. The pending request and automatic partial occurrence stayed held. Old button and direct old request decision were rejected, revoked authority denied, fresh approval committed once against the original occurrence. Ledgers intact and uncertain slots never reclaimed. |
| E14 | Unauthorized Telegram and API use | Foreign identities have no side effects | **PASS.** Wrong user/callback ignored. Altered, stale and wrong-key envelopes denied. Restored roles had no underlying projection bypass grant. |
| E15 | Invalid, boundary and disputed inputs | Clarify invalid time, withhold unsafe interpretation | **PASS.** Native relay rejected invalid clock and unsupported location, withheld an ambiguous historical instant, and marked disputed sunrise withheld without writes. Skipped and exceptional annual dates stayed withheld. |

The complete native command exited 0. The additional E15 cases ran separately
via the calendar-only option. See [the Cycle 7 runner](../tests/integration/m2h_cycle7.py),
the [recurrence](../tests/integration/m2h_cycle5.py),
[historical](../tests/integration/m2h_cycle6.py) and
[cross-cluster](../tests/integration/m2h_cross_cluster.py) cases.

Twenty-nine focused parser, calendar, application and baseline diagnostic
tests passed. Explicit source checks and manifest verification passed. The
PR stack was verified from #10 through #4. Prior migration and relay bytes
are unchanged. The added fence uses scoped authority, and the preserved
partial actions stay visible for review without becoming executable.

## Expanded calendar evidence

| Independent evidence | Test and measured result |
| --- | --- |
| Drik Delhi displays Chaitra Shukla Navami ending 13:20 on 15 April 2027. A separate Delhi table displays 13:21. [Drik interval](https://www.drikpanchang.com/iskcon/lord/rama-navami-date-time.html?time-format=24plushour&year=2027) · [Dhyayan day table](https://astro.dhyayan.com/panchang/2027-04-15) | Calculation 13:21:24 IST, within the existing 90-second display comparison. The guard selected 15 April. The published interval serves as calendar evidence only. |
| Delhi's April calendar and the second publisher's daily tables show Shukla Dwadashi over two April 2023 sunrises. [Drik Delhi calendar](https://www.drikpanchang.com/download/hindu-calendar/2023/delhi/purnimanta/Hindu-Calendar-2023.pdf) · [Hindu Calculator](https://hinducalculator.com/indian-calendar/2023/?m=4) | Both dawns ordinal 12. At 07:00 on 3 April the instant is already Trayodashi. A recurrence without an explicit repeated-date policy is withheld. |
| Drik Delhi lists Adhika Shravana, Shukla Tritiya, on 20 July 2023. [Drik Delhi](https://www.drikpanchang.com/panchang/day-panchang.html?date=20%2F07%2F2023&time-format=24hour) | The historical interval and dawn both yielded Tritiya. Amanta and Purnimanta preserved Adhika identity. |
| Historical Indian calendar identifies Kshaya Magha in January 1983. [myPanchang](https://www.mypanchang.com/historycalformat.php?cityhead=Indian&cityname=IST&mn=1&monthtype=1&yr=1983) | This corroborates the exceptional month only. Historical calculation yields ordinal 9 on 23 January. Both month labels stay unsupported. |
| Cycle 6's validated 2023 month boundary, 1995 comparison, and 2027 skipped/selected targets. [Prior evidence](M2H_CYCLE6_HISTORICAL.md#independent-checks) | Retained the distinction between historical instant and annual civil date. Delhi 1995 publisher coverage remains incomplete. |

The 300-second sunrise guard remains distinct from the display budget and the
event-instant uncertainty check. Coverage is limited to the cited cases.
Other locations and festival rules remain outside release scope.

## Remaining release decisions

- [x] Complete simulated end-to-end matrix and cross-cluster recovery. Use the
  [partial-approval recovery procedure](M2H_CYCLE7_RECOVERY.md) in development.
- [x] Preserve Cycle 6 exact-schema and original source evidence.
- [ ] Run the focused Cycle 7 check below against the authorized schema for the
  new 0014 fence and revised approval behavior.
- [ ] Record owner decisions for [individual source artifacts](M2B_CYCLE7_DECISIONS.md).
- [ ] Review the bounded live wrapper and obtain fresh owner authorization
  for [the six-message private test](M2H_CYCLE7_PRIVATE_ACCEPTANCE.md).
- [ ] Separately approve any release, authoritative source promotion or live
  lunar scheduling.

## Reproduction and single WSL handoff

Use the verified DE440s and pinned local dependencies.

```bash
OPENBLAS_NUM_THREADS=1 python -B tests/integration/m2h_cycle7.py \
  --pg-bin /path/to/postgresql/17/bin --pg-share /path/to/postgresql/17/share \
  --ephemeris "$DINCHARYA_PUBLIC_DE440S" --n8n /path/to/n8n --year 2027
```

**One WSL task.** In the original authorized checkout, select the Cycle 7 draft
head. Use the existing pinned daemon and exact previously authorized schema-only
file. Report fixed stage headings and exit code to
[issue #6](https://github.com/vasu1765/dincharya-ai/issues/6). The check stages
the fence in the same disposable database. Independently recreated roles
already ran across clusters in Work. The Work preflight exited 2 before
Docker because the authorized file was absent.

```bash
OPENBLAS_NUM_THREADS=1 python -B tests/integration/m2h_cycle7_baseline.py \
  --expected-daemon-id 44c1ef83-c50e-4ecc-8f19-4b112bc40f29 \
  --ephemeris "$DINCHARYA_PUBLIC_DE440S" --year 2027 --execute-approved
```
