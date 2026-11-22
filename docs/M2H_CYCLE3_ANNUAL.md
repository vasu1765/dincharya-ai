# Milestone 2, Cycle 3 annual lunar scheduling and recovery

Cycle 3 uses the existing scoped lunar approval and reminder APIs. One durable
annual rule can project a separate appointment for each civil year. The
development gate remains off by default. The development gateway registers
no delivery tick and the runtime rejects a reminder transport in this mode.

## Review workflow

| Action | Result |
| --- | --- |
| Add “every year”, “हर साल” or “har saal” to a Cycle 2 request with an explicit civil start year | Show the named lunar month, paksha, tithi, Amanta/Purnimanta, ordinary or Adhika, repeat choice and IST time. Confirm stores the rule and its approval audit in one database transaction. |
| `/lunar_rules [after-series-id]` | List up to ten owner-scoped durable annual rules and show the next-page cursor when applicable. |
| `/lunar_year SERIES YEAR` | Calculate a single eligible Delhi date in that Gregorian year. The preview shows the exact appointment. Confirm creates the native one-off appointment within the existing conflict and fingerprint checks. |
| `/lunar_rule_status SERIES` | Show whether the annual rule is active and list its active projected appointments. |
| `/lunar_year_cancel SERIES OCCURRENCE` | Preview cancellation of one projected appointment. Confirmation leaves a tombstone and preserves delivery history. |
| `/lunar_rule_cancel SERIES` | Preview cancellation of the rule and its current appointment manifest. Approval fails if the manifest changes in the meantime. Confirm disables the series and cancels eligible pending work. |

Annual mode requires one named lunar month and a single choice of ordinary or
Adhika. An Adhika rule is evaluated in each requested year and yields no
appointment when that month is absent. Explicit first/last resolves repeated
sunrises. A skipped tithi, Kshaya, multiple matching dates, profile disagreement,
or uncertain boundary yields no appointment. The Drik Delhi primary and IMD
PAC secondary policy, 90-second publisher diagnostic and 300-second sunrise
guard are inherited from Cycle 1.

Review one year at a time, within the current Delhi civil year and the next five,
at or after the saved start year and through 2099. Each year requires a fresh
appointment approval. A calculated date in the past is withheld. There is no
background generation or automatic yearly approval. The ordinary Cycle 2
one-off flow stays available.

## Cycle 2 review and recovery

- The Cycle 2 signed Telegram envelope, private owner check, bounded button
  store, request fingerprint and existing database conflict checks are reused.
  Cycle 2 re-entry derived a series ID from a particular lunation and did not
  store discoverable rule details. Annual identity now stays stable across
  civil years, using the title, time and lunar rule identity. Changing the
  initial year, repeat choice or profile in a duplicate request fails closed.
- A rule with no confirmed appointments appears in `/lunar_rules`. After
  restart or preview expiry, use `/lunar_year` to regenerate a preview from the
  saved rule. Prior buttons become invalid. Pending reviews live for up to
  30 minutes. Annual decision expiry is checked in PostgreSQL after acquiring
  the shared write lock. A failed validation creates no appointment.
- Replaying the same calculation reuses its logical lunar occurrence. An
  additive database trigger also enforces one projected appointment per annual
  series per civil year, including cancelled projections, and the stored
  title/time. It applies to the older scoped decision API as well. The existing
  event/date reminder uniqueness remains in force. The 64-active-appointment
  manifest limit keeps whole-series cancellation available.
- Cancelling a preview discards or rejects that request. Cancelling a committed
  occurrence is a new reviewed decision. A cancelled occurrence cannot be
  resurrected by reprojecting its year. Existing sent or uncertain delivery
  history stays intact and an in-flight send blocks cancellation.
- In astronomical development mode, the signed service exposes the development
  operations and its disabled-delivery tick. Fixture-only request and
  approval routes remain in the existing synthetic fixture mode. Pending
  review handles are kept in a single service process. Multiple-service
  coordination and background recurrence remain outside this checkpoint.

## Integration and provenance

The repository contains an invented cycle-test schema and a repository-owned
inactive n8n relay fixture. The original schema-only application snapshot was
previously used under specific authorization for isolated acceptance. It is
outside Git and was not opened for Cycle 3. The source-adoption documentation
still lacks the exact original provenance manifest path. Historical published
and current workflow bodies and state are separate, and Code review/adoption
remains gated. Neither the invented schema nor the current relay can establish
the provenance of that older workflow or certify the application baseline.

Use the standalone command in [Cycle 2](M2H_CYCLE2_TELEGRAM.md), with PostgreSQL
17 and the pinned public ephemeris. Migration 0010 is synthetic-only and the
harness applies it over the existing checksummed migrations. The test uses real
PostgreSQL and the Telegram SDK, simulated Telegram/n8n traffic, and invented data.
It exercises restart recovery, cancellation before and after projection,
manifest staleness, annual duplicate suppression and reminder materialization.

### Remaining Milestone 2 gates

| Area | Remaining evidence or decision |
| --- | --- |
| 2B source provenance | Exact owner-authorized manifest or an owner decision to define a new reviewed source-adoption route. Validate the manifest alone before reading any separately approved referenced inputs. Resolve schema adoption, current/published workflow provenance and Code/state handling. |
| 2D application integration | Run the managed application route over the reviewed schema and real isolated n8n relay. Verify scoped role/ACL compatibility and no second scheduler. |
| 2E/2G operational acceptance | Finish supervision, migration and restore rehearsal, outage recovery, and advance reminders. Delivery reconciliation remains separately gated. |
| 2F calendar adoption | Broaden Delhi date validation, including boundary and month exceptions. Festival observance and live annual scheduling require separate approval. |

Recommend the next acceptance run use the real native n8n relay, a fresh
isolated PostgreSQL instance with the exact separately authorized schema-only
baseline, and simulated Telegram throughout. Verify checksums, roles, a process
restart between approvals, two annual projections, and one ledger row per
projected event/date. Reuse the prior private reminder evidence. The already
documented 2B provenance gap remains a release blocker even if this targeted
acceptance run passes.
