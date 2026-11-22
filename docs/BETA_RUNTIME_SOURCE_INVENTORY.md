# Integrated Personal Beta — revision-pinned source inventory (development)

Prepared 22 November 2026 from GitHub repository
`vasu1765/dincharya-ai`, **review reference**
`894f32392185c26e7a59c390d337a62b564b9b8c`
(on `development/m2g-telegram-integration`).
The SHA is a **source-review pin**, not an approved deployed/runtime revision.
The current documents subsequently evolve on the same development branch.
All Git blob IDs below were read from that explicit Git commit, not inferred
from file names. The values are Git content identifiers, not signed releases
or assertions about running containers.

## Source map and preliminary disposition

| Source | Git blob SHA-1 | Disposition |
| --- | --- | --- |
| `telegram-gateway/gateway.py` | `a90b0ab133fc687204c63063788bc698d64e8103` | Candidate: owner-only Telegram gateway; verify opt-in and startup behavior |
| `telegram-gateway/lunar_handlers.py` | `5bdb78b57f1d69868eb257afcc09ac9de14c3b66` | Candidate: signed user/approval bridge; no general lunar release |
| `telegram-gateway/reminder_handlers.py` | `a8a2b6a2b8710b1de03382ddbbdc65076e0352f5` | Candidate: opt-in reminder SDK |
| `telegram-gateway/lunar_acceptance.py` | `00e0e5f2e8fd6258dbe50f860f2ef28a3d2a1618` | Historic bounded live acceptance entry; **not** ongoing beta launcher |
| `telegram-gateway/requirements-m2g.txt` | `bde0c5278ba5096c5808436d979d6773c05bfe9f` | Acceptance dependency pins; verify a clean beta environment independently |
| `dincharya/reminders.py` | `515e628d706ab1b330e6ecc23ea975e6de6701ee` | Receipt-required worker |
| `dincharya/reminder_adapters.py` | `e5ed9c25f049ac6a5e95c11c187a81782202d6e8` | Restricted receipt-backed persistence + transport |
| `dincharya/lunar_runtime.py` | `4d4d2238230409a0dd8a1c68a83653440ad378ef` | Acceptance-only opt-in runtime; **not** approved personal deployment |
| `dincharya/lunar_service.py` | `8ed7b11bef76b904ca0ecf81c3c7528ea5d6ae30` | Signed lunar service in development |
| `database/migrations/0015_managed_receipt_safety.sql` | `dd4d76d4855f08c79c224128979d44efb57ee100` | Synthetic-only migration; tested in fresh PostgreSQL 17 |
| `workflows/m2g-lunar-acceptance.json` | `f79027b0e8534a2978ffb4080e87d2569ed57873` | Inactive Webhook+HTTP Request acceptance relay, not live workflow |
| `tests/integration/receipt_candidate.sh` | `2042d153481878543cd03b945eb48da59df51132` | Accepted disposable PG17 receipt validation; do not rerun without reason |
| `tests/integration/compose.json` | `1ae4134386b86ac1e03bfc86dcbff4b355d7284e` | Synthetic integration stack; never become real personal volume |
| `staging/laptop/service.py` | `3d871f3a39dae746d622915cfd9a62f59cffba95` | Stage 1/2 synthetic recorder and recovery services only |
| `compose.yaml` | `e76126cdbb98718e4ad194147acd6fd4ad08bc5e` | Existing general stack, **not** verified pin-safe personal-beta deployment |
| `docs/m2b-repository-review.json` | `b51199505cb3a2f231b4e6e494fcf5bd3bffae81` | Existing digest-bound source proposal; no owner adoption in this record |

**Important:** `0015` checks database name `dincharya_app_test` and
`session_user=synthetic_test`. Do not lift that migration into a persistent
personal database by changing the guards. The **authoritative schema and
migration adoption remains a new reviewed source decision**. Likewise, do not
turn the inactive n8n relay into a live workflow implicitly.

## Operating and deployment gaps

1. **Baseline adoption:** identify the actual authorised schema versus the
   synthetic fixture; complete the M2B digest-bound artifact decisions. Confirm
   migrations through 0015 can be expressed as an additive, safe,
   separately reviewed personal-beta migration chain; do not rewrite history.
2. **Dependency/service pinning:** the accepted tests used PostgreSQL 17 and
   n8n 2.47.3 (nodes-base 2.47.2). Current `compose.yaml` refers to mutable
   `postgres:17` and `n8nio/n8n:latest` in the original architecture.
   Actual runtime image digests need approval and a fresh explicit beta
   configuration, not implicit deployment.
3. **Secrets and routing:** a new dedicated owner-bound bot identity, private
   numeric recipient, distinct signing keys, network bindings and scoped worker
   login require exact beta preflight. Do not read existing secrets to prepare
   this inventory.
4. **Start/stop:** create a verified fresh personal DB and immutable ledger,
   single worker/poller, disable all outbound Telegram by default, and support
   clean manual stop and quarantine after uncertain delivery.
5. **Reliability:** independent monitor capable of observing a complete host
   outage; owner-visible alert, healthy-media daily encrypted off-device backup,
   independently tested restore, and old-host fencing. A same-host healthcheck
   cannot substitute for the independent observer.
6. **Functionality:** initially bound real use to Gregorian routines and
   guarded read-only Panchang. Unsupported annual lunar/festival projections
   stay withheld. Ollama unavailability must not stop deterministic reminders.

## Work handoff / next validation boundary

For the next implementation candidate, prepare an **entirely new disabled-by-
default beta runtime**; do not copy/rename the Stage 1/2 test Compose or use
its databases as live state. Review service image IDs and effective grants
against the exact target. If changes require native PostgreSQL/Docker tests,
prepare one consolidated Acer WSL Codex task, use new disposable namespaces
and record sanitized results.

Gate 1 requires separately authorized **attended** test-bot use with a fixed
message budget and time window. Gate 2 is a separate owner authorization after
independent monitor + backup/restore validation. Source review **does not
authorize** WhatsApp integration, live messages, production, VPS, `main`
merge, historical Code execution or existing backup access.
