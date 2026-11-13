# Isolated Panchang feasibility prototype

Experimental astronomy only, **not a scheduling engine**. No database, n8n,
Telegram, festival rules, production credentials or private inputs are involved.
See [feasibility report](../../docs/M2F_FEASIBILITY_RESULTS.md). The prototype
implements geocentric elongation/transitions, Delhi sunrise hypotheses, physical
Amanta/Purnimanta boundaries and a generic tithi preview with review flags.
Month names, validated Lahiri, general Adhika/Kshaya and annual anniversaries
explicitly raise Unsupported. No persistent schedule or reminder API exists.

## Pinned environment and public assets

Tested: Linux x86_64, CPython 3.12.3. requirements.txt pins **all six reviewed
packages (including research-only pyerfa) and the exact downloaded wheel hashes**; numpy/sgp4 wheels are specific
to CPython 3.12/Linux x86_64. This is not a cross-platform lock. Do not silently
substitute another build. Package versions, filenames, wheel hashes, DE440s
source/size/hash and bundled timescale/nutation hashes are in ephemeris.json.
The system Asia/Kolkata TZif bytes are hash-pinned too; runtime uses those bytes,
not ambient PYTHONTZPATH. New artifacts need explicit metadata review.

Acquisition is separate from runtime. The accepted public kernel URL is:
https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de440s.bsp

Obtain that public file into a dedicated directory **outside Git**, verify the
size and SHA-256 against ephemeris.json, and use an explicit local path. The stored
hash was computed from the HTTPS acquisition, not an independently signed JPL
checksum. No BSP/wheel is committed. Missing, symlinked, nonregular, wrong-size or
wrong-digest kernel data fails closed; no automatic download or fallback engine.
The Linux loader retains an O_NOFOLLOW verified fd and opens its /proc fd inode.
An adversarial same-user/host mutation of an open file is outside this prototype's
trust model; checksums are integrity checks, not source authentication.

For reproduction after separately authorized public package acquisition, create
an external venv and use only the reviewed wheels (replace the placeholders):

```bash
python3 -m venv /tmp/dincharya-panchang-repro
PIP_CONFIG_FILE=/dev/null /tmp/dincharya-panchang-repro/bin/python -m pip install \
  --no-index --no-cache-dir --find-links /EXTERNAL/REVIEWED_WHEELS \
  --require-hashes -r prototypes/panchang/requirements.txt
```

Do not reuse production environments or read package-index credentials. Approved
session environment was /tmp/dincharya-m2f-feasibility-9524757; it can expire.
Requirements hashes also allow a separate explicit public PyPI download, but the
prototype never invokes pip or downloads anything. Dependencies' licenses and
public data notices remain with their distributions; no AGPL astronomy library
or algorithm implementation is included/copied. Engine adoption is not approved.

## Focused execution, from repository root

```bash
DINCHARYA_PUBLIC_DE440S=/EXTERNAL/PUBLIC/de440s.bsp \
  OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  /tmp/dincharya-panchang-repro/bin/python -B -m unittest discover -s tests/panchang -v

OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  /tmp/dincharya-panchang-repro/bin/python -B -m prototypes.panchang.feasibility \
  --ephemeris /EXTERNAL/PUBLIC/de440s.bsp
```

CLI adds Python audit guards rejecting socket connection/DNS/bind events before
importing astronomy, and Linux 512 MiB address-space/60-second CPU limits. This
is not an OS network namespace or defense against malicious native code. All
runtime inputs/data are local; dependency acquisition/research was online. Tests
also patch socket connections. Keep the one-thread BLAS setting for reproducible
resource measurements. No import-time service, subprocess or HTTP call occurs.

CLI exits **2** with status feasibility_incomplete_not_for_scheduling and
usable_for_scheduling=false; this is an intentional failed release gate, not a
successful calendar-adoption result. Exit 1 means invalid/unavailable input or
execution failure, with sanitized diagnostics. Exact astronomy outputs repeat for
identical input/version/profile; timing/RSS vary. Solving the same boundary from
different brackets can differ by less than the declared 0.05-second bracket.

feasibility-results.json is the sanitized recorded run, including public numeric
comparisons and measured performance, not a private capture. The original eleven test passes
mean scoped code/regression checks; they do **not** turn the two failed independent
tithi comparisons into passes. Sunrise's single rounded reference is numerically
close but its exact coordinates/model are unconfirmed. Annual lunar dates are
withheld. Do not increase tolerances or implement guessed month labels to pass.

Instant computations are bounded to 1900–2100 UTC with internal bracketing pads
inside the kernel coverage. Endpoints are tested for computability, not historical
or future UTC accuracy. Monthly preview is bounded to 366 days and may reject
edge windows whose supporting sunrise dates leave the accepted range. Public
fixtures contain no personal birth/schedule data. All sampradaya/festival choices
remain research labels; no owner religious identity is inferred.

## Focused validation follow-up

Latest research baseline is pushed at 6f1f0b7 on
`development/m2f-skyfield-feasibility`. Run the same focused test command above
(23 tests), then the new offline comparison runner:

```bash
OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  /tmp/dincharya-panchang-repro/bin/python -B -m prototypes.panchang.validation \
  --ephemeris /EXTERNAL/PUBLIC/de440s.bsp
```

Exit 2 intentionally retains failed scheduling adoption. See validation-results.json
and research-references.json for all nine coordinate hypotheses, mixed additional
tithi evidence and selected explicit Lahiri/Amanta research checks. Original
references.json and feasibility-results.json are preserved historical evidence.
The ERFA experiment is separate from the default astronomy calculation; no Swiss
library/code is included. Public month_label/annual_preview still raise Unsupported.
The PDF research parser is not a runtime requirement and publications remain external.

Raw point computations use 1900–2100 UTC; complete returned intervals must also
lie wholly in that range. Only transition/preview end parameters accept the 2101
exclusive end sentinel. Internal padding never authorizes outside calendar claims.
Raw tithi_at is a point estimate; interval, month-boundary and transition-search
endpoint membership within 0.1 s of solved boundaries rejects as numerically
ambiguous. Existing 120 s review and 60 s external accuracy gates are unchanged.
Jan 1, 1900 sunrise computes but its straddling interval rejects. Jan 2, 1900 and
Dec 31, 2100 monthly previews have focused passing fixtures; partial edge intervals
reject. Neither endpoint computability nor selected month evidence is global
astronomical accuracy certification.

## Evidence-bounded month research

From pushed timing checkpoint 452bbcd, month_research.py adds separate labelled
Amanta/Purnimanta candidate conversion and annual_example. Public/general
Astronomy.month_label/annual_preview remain Unsupported. Read month-references.json
and month-results.json: only 21 selected dates over 2023–2025 and 15 exact rule/year
preview combinations are evidenced. Purnimanta direct labels versus context
inferences are explicit. Unknown combinations reject; no Kshaya name or skipped
fallback is guessed. Research identities and Chaitra-anchor tokens are not database
IDs or era-year conversions. All outputs are unusable for scheduling.

```bash
DINCHARYA_PUBLIC_DE440S=/EXTERNAL/PUBLIC/de440s.bsp \
  OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  /tmp/dincharya-panchang-repro/bin/python -B -m unittest discover \
  -s tests/panchang -p test_month_research.py -v

OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  /tmp/dincharya-panchang-repro/bin/python -B -m prototypes.panchang.month_validation \
  --ephemeris /EXTERNAL/PUBLIC/de440s.bsp
```

Runner intentionally exits2, checks preserved accepted evidence hashes, blocks
runtime network and uses existing resource limits. Research fixture metadata pins
public documents, exact selected pages and qualifications; no raw publication is
committed. A full example run currently uses about 40.5 CPU seconds on this host;
bounded back-search has not been optimized/certified for a small VPS. No package,
ephemeris or existing fixture change is needed. Stop for review; this is not final
month-engine or scheduling adoption.

## General personal recurrence research (base2bd37c0)

recurrence.py adds fixture-independent LunarRule/RecurrenceResearch annual,
monthly and bounded preview APIs. Separate from old annual_example and disabled
Astronomy scheduling APIs. See [full API/identity/date-gate design](../../docs/M2F_RECURRENCE_PREVIEW.md).
Rules accept month (annual) or no month (monthly), paksha/day1–15, explicit
ordinary/adhika/both, convention and repeated=review/first/last. Birth interpretation
must explicitly choose instant or sunrise. Date assignment remains sunrise-based.
Unknown names/contexts, skipped/uncertain and Kshaya have no selected date.

```python
from prototypes.panchang.astronomy import Astronomy
from prototypes.panchang.recurrence import LunarRule, RecurrenceResearch
with Astronomy('/EXTERNAL/PUBLIC/de440s.bsp') as astronomy:
    preview = RecurrenceResearch(astronomy)
    result = preview.annual(LunarRule('shukla', 9, 'ordinary', month='chaitra'), 2026)
    assert result['usable_for_scheduling'] is False
```

```bash
DINCHARYA_PUBLIC_DE440S=/EXTERNAL/PUBLIC/de440s.bsp \
  OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  /tmp/dincharya-panchang-repro/bin/python -B -m unittest discover \
  -s tests/panchang -p test_recurrence.py -v

OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  /tmp/dincharya-panchang-repro/bin/python -B -m prototypes.panchang.recurrence_validation \
  --ephemeris /EXTERNAL/PUBLIC/de440s.bsp
```

The runner deliberately exits2. calendar-references.json and recurrence-results.json
record separate selected date and unchanged60-second timing gates. Date matches do
not approve engine adoption. Month LRU32/preview LRU8/sunrise800 bound memory;
profile changes reject and cache outputs are deep copies. Evaluator owns its
Astronomy cache and is single-threaded. No persistence, networking or live sends.

## All-name coverage / logical identity v2 (base0a1cae6)

All12 names have selected research evidence; not general certification. New
coverage-references.json and coverage-results.json preserve older accepted bytes.
Read [coverage matrix, logical contract and proposed date gate](../../docs/M2F_MONTH_COVERAGE.md).
Logical identityv2 excludes model/profile/date/policy; provenance is separate.
Offline reconcile_calculations compares previews only and withholds changed dates;
unknown/legacy/duplicate/changed identity sets reject. No stored or delivery action.
The preview loop now correctly applies300 seconds, while original60-second timing
diagnostics and pinned model remain unchanged. Do not adopt or blindly migrate keys.

```bash
DINCHARYA_PUBLIC_DE440S=/EXTERNAL/PUBLIC/de440s.bsp \
  OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  /tmp/dincharya-panchang-repro/bin/python -B -m unittest discover \
  -s tests/panchang -p test_coverage.py -v

OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  /tmp/dincharya-panchang-repro/bin/python -B -m prototypes.panchang.coverage_validation \
  --ephemeris /EXTERNAL/PUBLIC/de440s.bsp
```

Affected test_recurrence.py also passed; no unrelated suites needed. Runner exits2
with incomplete adoption gate. All work remains offline, no DB/n8n/Telegram changes.

## Bounded pre-integration assessment (base34b6270)

See [readiness matrix/policy/next approval gate](../../docs/M2F_PREINTEGRATION_ASSESSMENT.md).
The research comparator rejects application approval/delivery payloads and withholds
changed birth/repetition policy even when the civil date is unchanged. It cannot
edit approved occurrences or send reminders; persistence safety is not certified.
No integration adapter is implemented.10 prior evidence files remain unchanged.

```bash
DINCHARYA_PUBLIC_DE440S=/EXTERNAL/PUBLIC/de440s.bsp \
  OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  /tmp/dincharya-panchang-repro/bin/python -B -m unittest discover \
  -s tests/panchang -p test_preintegration.py -v
```

preintegration-results.json records the bounded run/public fixtures and two affected
comparison regressions. No need to rerun unrelated integration/timing experiments.
