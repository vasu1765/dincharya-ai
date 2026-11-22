# Personal beta — development implementation checkpoint and Acer verification

Review date: 22 November 2026. This is a **source-only development
checkpoint**, not an approved deployment. It belongs to the
[combined Stage A+B milestone](INTEGRATED_PERSONAL_BETA.md).

## What exists now

- `docs/BETA_RUNTIME_SOURCE_INVENTORY.md` / `docs/beta-source-pins.json`:
  exact 16-source review inventory. Source bytes are review pins, not release
  adoption, deployed image identities or an authority to send messages.
- `scripts/check-beta-source-pins.py` and
  `tests/test_beta_source_pins.py`: fail-closed offline byte checks;
  preserve the earlier evidence and do not claim full integration from them.
- `docs/beta-runtime-plan.json`: inert initial service/configuration plan.
  All five conceptual services (`postgres`, `n8n`, `gateway`, `scheduler`,
  `worker`) are disabled; exact image IDs are still **pending**.
  All messaging, startup, and source-promotion flags are explicitly false.
- `dincharya/beta_preflight.py` and
  `tests/test_beta_preflight.py`: offline validation for release-plan
  structure, immutable image pin format, fresh isolated personal database,
  non-execution, monitoring and backup status, and forbidden secret fields.

The new beta preflight **does not inspect Docker**, create a PostgreSQL
database, read secrets, start workers, or prove that a personal-beta
configuration is safely executable. It must never be mistaken for runtime
authorization or a substitute for the existing historical acceptance.

## One consolidated Acer Codex read-only task

Use the existing clean approved development checkout; do **not** relocate
`.git`, alter read-only Git metadata or change Docker permissions.
Use a verified Python 3.12 interpreter and no production credentials.
If metadata is restricted, an extracted read-only working tree is sufficient
for these Python-only checks. Never invoke Docker for this first verification.

```bash
python3 -B -m unittest discover -s tests -p test_beta_source_pins.py -v
python3 -B -m unittest discover -s tests -p test_beta_preflight.py -v
python3 -B scripts/check-beta-source-pins.py
python3 -B -m dincharya.beta_preflight docs/beta-runtime-plan.json
python3 -B -m compileall -q dincharya/beta_preflight.py scripts/check-beta-source-pins.py tests/test_beta_preflight.py
```

Run the commands against the same exact revision; record that revision,
individual exit codes, number of executed tests and sanitized PASS lines.
If a source pin legitimately changes, **stop**; do not change the pinned
manifest silently to make a failure disappear. Confirm the reviewed source
change and regenerate the pin under a separate documented decision.
No production, personal database, existing Stage 1/2 volumes or Telegram
credentials are needed.

## Implementation before Gate 1

1. **W1 — M2B source dispositions:** produce and approve an exact artifact
   package for personal-beta scope. The synthetic-only 0015 migration
   must not be transplanted by removing database guards; design and review
   a real migration chain with safe role grants and existing schema adoption
   only at a separately approved boundary.
2. **W2 — fresh runtime:** supply immutable image digests, distinct roles,
   private socket/loopback bindings, one polling gateway and worker, fail-closed
   explicit egress gate, and a new app database distinct from acceptance
   databases. Prepare dry-run code/config without startup.
3. **W3 — operations in parallel:** independent monitor, owner-visible outage
   alert, healthy off-device encrypted daily backups and independent restore.
   These may be prepared alongside W1/W2 but do not qualify unattended
   operation until separately tested and authorized.
4. **W4 — functionality:** deterministic routine creation, approval, conflict,
   reminder and lifecycle tests with only simulated messaging; guarded
   historical Panchang read-only. No unvalidated festival/annual lunar
   recurrence and no other orchestrators.
5. **W5 — WhatsApp:** documentation/interface contract only; Telegram remains
   sole active transport. Provider eligibility and billing need fresh review
   before any actual integration.

### Acceptance boundaries

**Gate 1 (attended):** only after W1 adoption and W2/W4 validation, obtain a
new owner-approved exact revision, private bot identity, permitted activities,
IST window and outbound message count. Manual start, attended stop, receipt and
uncertainty verification. Previous one-use live Telegram authorization is
consumed.

**Gate 2 (unattended):** only after Gate 1, independent outage alert and
backup/restore/fencing evidence, obtain separate owner authorization for
ongoing messages/startup. No production/VPS/main merge is implied.
