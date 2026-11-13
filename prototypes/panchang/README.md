# Isolated Panchang feasibility prototype

Experimental astronomy only, **not a scheduling engine**. No database, n8n,
Telegram, festival rules, production credentials or private inputs are involved.
See [feasibility report](../../docs/M2F_FEASIBILITY_RESULTS.md). The prototype
implements geocentric elongation/transitions, Delhi sunrise hypotheses, physical
Amanta/Purnimanta boundaries and a generic tithi preview with review flags.
Month names, validated Lahiri, general Adhika/Kshaya and annual anniversaries
explicitly raise Unsupported. No persistent schedule or reminder API exists.

## Pinned environment and public assets

Tested: Linux x86_64, CPython 3.12.3. requirements.txt pins **all five transitive
packages and the exact downloaded wheel hashes**; numpy/sgp4 wheels are specific
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
comparisons and measured performance, not a private capture. Eleven test passes
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
