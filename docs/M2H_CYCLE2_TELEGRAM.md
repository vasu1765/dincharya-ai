# Milestone 2, Cycle 2 Telegram lunar approvals

The development path converts a bounded English, Hindi or Hinglish request to
one personal lunar appointment. It uses the [Cycle 1 date policy](M2H_CYCLE1_ACCURACY.md),
the existing lunar PostgreSQL approval API, the native Gregorian projection
and the existing reminder worker. Production lunar scheduling stays disabled.

## Owner flow

1. In the private bot chat, send a lunar request with a quoted title, paksha,
   tithi, Amanta or Purnimanta, ordinary or Adhika month selection, a search
   year or an ISO civil date window, and one 24-hour IST time. Supply the
   lunar month for a birthday or wedding anniversary. Give a first or last
   preference if the tithi spans two sunrises. The gateway also accepts
   `/lunar_preview` followed by the same request.
2. The parser asks for clarification when required details are missing or
   conflicting. Resubmit the complete request with the missing fields.
   Supported aliases cover English, Devanagari Hindi and common Hinglish,
   including Devanagari digits. The language layer has no database authority.
3. A valid preview shows the tithi, convention, ordinary/Adhika identity,
   repetition policy, applicable Delhi sunrise dates, selected appointment
   date and time in IST, and that the reminder is due at the start.
   Confirming this preview approves the rule. Cancel discards the draft.
4. The occurrence preview shows the exact appointment and number of existing
   appointments on that date. A second authenticated Confirm creates the
   appointment through the existing PostgreSQL API. Cancel rejects the
   pending occurrence. Overlaps use the existing conflict policy and
   cannot be force-approved from this interface.

| Language | Example |
| --- | --- |
| English | Remind me "Family puja" on lunar Chaitra Shukla Navami, Purnimanta, ordinary, first, in 2027 at 18:00 IST. |
| Hindi | मुझे "परिवार की पूजा" की तिथि चैत्र शुक्ल नवमी पूर्णिमांत सामान्य पहली २०२७ में १८:०० बजे याद दिलाओ। |
| Hinglish | Mujhe "Family puja" Chaitra Shukla Navami tithi purnimant samanya pehli 2027 mein 18:00 baje yaad dilao. |

The initial parser is deterministic and bounded. Birth-time inference,
relative dates, automatic multi-occurrence projection and festival observance
are outside this path. A wide window producing multiple eligible results
requires clarification with a narrower window. Explicit month and tithi rules
use the existing identity, including the lunation cycle and ordinary/Adhika
distinction. The service rejects past appointments.

## Approval and delivery boundaries

- The normal gateway has no lunar development handlers. The service flag
  `development_astronomy` defaults to false and must be a boolean. Enabling
  it requires a verified local public DE440s kernel and the existing isolated
  PostgreSQL configuration with distinct owner, calculator and worker logins.
  A matching enabled profile in the isolated profile table is required by SQL.
- The development Telegram adapter is isolated from the previously authorized
  fixture reminder acceptance mode. The adapter has no tick registration and
  requires separate Telegram approval, the dedicated bot identity, private
  config and explicit launch acknowledgement. Astronomical development mode
  rejects a reminder transport, including an injected one. The existing
  signed n8n envelope remains the route to the service.
- Only matching private Telegram owner updates can create or confirm a
  preview. Callback data contains a random opaque identifier. Review data is
  held for at most 30 minutes in a bounded process-local store. Restart
  invalidates pending buttons and requires a fresh preview.
- Recalculate the exact choice before both approvals. SQL additionally binds
  the occurrence review to the observation, conflicts and request fingerprint.
  Stable SQL action IDs and the occurrence uniqueness constraints protect
  against duplicates, including re-entry of the same appointment after a
  restart. The first approval can hold a rule with no projected appointment
  if the second step is cancelled, expired or refused.
- The publisher diagnostic is not used as a date uncertainty bound. A match
  between both sunrise models is required, and matching Drik/PAC transition
  evidence can expand the guarded uncertainty interval. A comparable Delhi
  label that conflicts with the calculation withholds selection. Publisher
  coverage is limited to the preserved evidence panel.

## Verification

The standalone development harness starts a disposable PostgreSQL 17 cluster on
loopback with synthetic data and scoped logins. It applies the existing
checksummed migrations over a deliberately invented test schema. No private
baseline, Telegram credentials, Docker stack or running n8n instance is needed.
The harness runs the real Telegram SDK, simulated Telegram transport, signed
application API, real PostgreSQL decisions and native reminder materialization.
It checks a foreign callback, both approvals, duplicate clicks, stale
observations, an existing conflict, concurrent decisions and cancellation.

```bash
export DINCHARYA_PUBLIC_DE440S=/absolute/path/to/de440s.bsp
export OPENBLAS_NUM_THREADS=1
python -B -m unittest discover -s tests -v
python -B -m unittest discover -s tests/panchang -v
python -B tests/integration/m2h_development.py \
  --pg-bin /absolute/path/to/postgresql/bin \
  --ephemeris "$DINCHARYA_PUBLIC_DE440S"
```

Use the pinned Panchang environment and the Telegram gateway acceptance
dependencies. For a relocated PostgreSQL installation, pass its share
directory with `--pg-share`. The integration fixture uses a future year with
an eligible Chaitra Shukla Navami. Pass `--year` when the default next civil
year is unsuitable for the fixture.

The relay and Telegram transport are simulated in this Cycle 2 run. Live bot
behaviour and compatibility with the authorized application baseline remain
separate acceptance work. Earlier private reminder delivery evidence remains
valid within its original scope. No live Telegram run is required for this review.
