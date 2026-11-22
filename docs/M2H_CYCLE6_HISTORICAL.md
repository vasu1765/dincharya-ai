# M2H Cycle 6 historical Panchang and recovery

## Telegram development interface

Use `/panchang` or ask a bounded question such as “What was the tithi on 6
December 2023?” A date-only question defaults explicitly to New Delhi, shows
the tithis at civil midnight and local sunrise, and lists boundaries during the
civil date. An exact-time question adds the event interval and both lunar month
conventions where supported. Delhi is the only verified geographic profile.
Historical offsets come from the pinned Asia/Kolkata TZif. Nonexistent and
ambiguous wall times require clarification.

Use `/lunar_from_event` or two sentences to propose an anniversary. Give the
historical date, local time and Delhi in the first. Give a separate future
time in the annual reminder sentence. Supported requests include English,
Hindi and Hinglish. This example is a synthetic fixture.

```text
I was married on 7 December 2023 at 4 AM in Delhi. Schedule a yearly Hindu-calendar anniversary reminder at 8 AM; Amanta; 1 hour before, at start
```

Optional semicolon clauses choose Amanta/Purnimanta, automatic/manual, first or
last repeated tithi (or review), and notification offsets. Purnimanta, automatic
approval mode, repeated-date review and at-start reminders are preview defaults.
The owner approves the displayed rule. The historical instant and derived
interval, convention and digest are persisted in the existing owner-scoped
approval audit only after confirmation. Confirmation recomputes the historical
evidence. An expired or restarted preview must be reopened. The Cycle 5
projector applies the separate Delhi sunrise guard when it selects future dates.

## Independent checks

| Synthetic query | Computed result | Comparison |
| --- | --- | --- |
| 6 December 2023, date only | Krishna Ashtami at the start of the civil date, Navami after about 00:38 and at sunrise | Delhi day publication confirms Navami at sunrise. [Drik Delhi](https://www.drikpanchang.com/panchang/day-panchang.html?date=06%2F12%2F2023&lang=hi) |
| 6 December 2023, 10:00 | Krishna Navami. Amanta Kartika, Purnimanta Margashirsha | The publisher's next boundary is 03:04 on 7 December. [Drik Delhi](https://www.drikpanchang.com/panchang/day-panchang.html?date=06%2F12%2F2023&lang=hi) |
| 7 December 2023, 04:00 | Krishna Dashami before sunrise. Amanta Kartika, Purnimanta Margashirsha | Delhi day publication confirms the month names and Dashami through roughly 05:06 on 8 December. [Drik Delhi](https://www.drikpanchang.com/panchang/day-panchang.html?date=07%2F12%2F2023) |
| 22 July 1995, 14:57 | Krishna Ekadashi at the instant, Dashami at sunrise. Amanta Ashadha, Purnimanta Shravana | Bundi comparison confirms a roughly 09:40 transition and both month names. Its sunrise is location-specific, and the Delhi source was unavailable for this date. [Shree Saket Panchang](https://shreesaketpanchang.com/home/monthlypanchang?mydate=1995-07-22) |
| 1995 example, 2027 anniversary | Withheld. Ekadashi starts after Delhi sunrise on 29 July and ends before sunrise on 30 July. | Both published Delhi sunrises are 05:41 and the tithi interval is displayed as 07:33 to 05:12 the following day. [Drik Delhi July table](https://www.drikpanchang.com/panchang/table/month-panchang.html?date=24%2F07%2F2027&lang=en) |
| 2023 example, 2027 Amanta anniversary | 23 November 2027 | Delhi day entry agrees on Krishna Dashami and Amanta Kartika. [Drik Delhi ISKCON edition](https://www.drikpanchang.com/iskcon/panchang/iskcon-detailed-day-panchang.html?date=23%2F11%2F2027&time-format=24hour) |

The 90-second diagnostic compares publisher display precision; the 300-second
guard applies to civil sunrise selection. The exact-instant path withholds
inside the computed numerical bound or the interval allowed by comparable
publisher precision. It does not import the sunrise guard. Historical month
labels use the existing bounded Lahiri model and explicitly report unsupported
months. The test suite retains Adhika, Kshaya, repeated/skipped tithi,
conflicting Delhi observations and the June 30 sunrise regression. Festival
observance requires a distinct policy and release approval.

## Operations and scope

The database lease permits one projection process at a time and records its
last successful check. `/recurring_health` returns owner-scoped slot backlog,
sending, quarantine, exhausted, and last confirmed slot due time, plus up to 20
quarantine records with no message bodies or credentials. The slot worker shares
the existing delivery lock. The fixture runner alone supplies the transport used
to test blockage, unknown acceptance and restart. Historical acceptance sets a
40-second relay budget in the disposable import. The original workflow file and
its timeout remain byte-for-byte intact.

The cross-cluster rehearsal recreates scoped groups and login roles independently,
restores a disposable dump, rebinds only fixture principals by exact role name,
and preserves original OIDs in immutable history. Automatic projection
re-executes after restore and uncertain slots remain terminal. Unfinished
decisions bound to old-cluster immutable action IDs still need a reviewed
recovery procedure before operational promotion. Fresh previews remain required
after a process restart.

### Reproduce

On 17 November 2026, the general suite reported 315 tests with six optional
skips. All nine historical tests and all 86 existing Panchang tests passed with
the pinned DE440s kernel. The source package verifier passed and rejected a
deliberately altered decision digest. The native n8n 2.47.3, PostgreSQL 17.12
and simulated Telegram reconstruction passed with exit 0. It covered migration
reapplication, scoped roles, signed relay outage and restart, owner approval,
read-only history, concurrency, cancellation, uncertain sends and cross-cluster
restore. Both disposable PostgreSQL clusters were shut down. The exact-schema preflight in Work
returned exit 2 before Docker because the previously authorized file was
unavailable.

```bash
python3 scripts/review-source-adoption.py --verify
python -B -m unittest discover -s tests
DINCHARYA_PUBLIC_DE440S=/path/to/verified/de440s.bsp python -B -m unittest discover -s tests -p test_historical_panchang.py
python -B tests/integration/m2h_cycle6.py --pg-bin /path/to/postgresql/17/bin --pg-share /path/to/postgresql/17/share --ephemeris /path/to/verified/de440s.bsp --n8n /path/to/n8n --year 2027
```

For the single WSL follow-up, use this branch in the original authorized
checkout and existing Python environment with the pinned dependencies. Run only
the following command and return fixed stage lines and exit code to issue #6.
The runner fails before Docker if the exact previously authorized input is not
at its named path. It opens no other schema path. No prior private Telegram
acceptance is needed.

```bash
OPENBLAS_NUM_THREADS=1 python -B tests/integration/m2h_cycle6_baseline.py \
  --expected-daemon-id 44c1ef83-c50e-4ecc-8f19-4b112bc40f29 \
  --ephemeris "$DINCHARYA_PUBLIC_DE440S" --year 2027 --execute-approved
```

| Gate | Cycle 6 scope | Remaining |
| --- | --- | --- |
| 2B | New review process and repository package | Owner artifact decisions and separate baseline promotion |
| 2D–2G | Synthetic migrations, signed relay, approvals, slot worker and cross-cluster recovery | Exact authorized-schema run for migrations 0011–0013; operational plan for partially approved actions after role rebind |
| 2H | Delhi historical read and reviewed personal anniversary | Additional independent reference coverage before live calendar adoption |
| Release | Simulated Telegram only | Separate production and live-delivery approval |
