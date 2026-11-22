# Integrated Personal Beta — combined Stage A+B implementation plan

**Decision:** 22 November 2026. Combine former Stage A (usable personal beta)
and Stage B (dependable operation) into one coordinated development milestone.
**Retain two separate operational acceptance gates:** a bounded attended
session first; independently monitored unattended use only after a second
review and authorization. The combined milestone does not shorten these gates.
See [laptop contract](LAPTOP_BETA.md), [development policy](DEVELOPMENT_POLICY.md),
[artifact review](M2B_SOURCE_ADOPTION.md) and [Stage 2 evidence](LAPTOP_STAGE2_RESULTS.md).

## Scope and initial behavior

- Sole active chat interface: **Telegram**, private owner-only bot. No live
  WhatsApp endpoint, credentials, webhook, business number, polling or egress.
- Initial functional slice: approved one-off, daily, weekly and Gregorian
  annual activities; explicit schedule review/approval, conflict detection,
  optional bounded advance reminders, pause/resume/cancel, and read-only guarded
  Delhi Panchang/historical lookups. Unsupported or disputed calendar inputs
  fail closed. General lunar/festival recurrence is **disabled** pending its
  separate accuracy and release gates.
- Model assistance is advisory; PostgreSQL authorizes durable state, not
  unstructured LLM output. Failure of Ollama must not interrupt deterministic
  reminders. No extra orchestrator, dashboard or mandatory habit tracking.
- Exclude existing private workflow adoption, historical Code execution, real
  source-data migration, routine production reconciliation or automatic resend,
  and unrelated active Telegram/production accounts.

## Development workstreams (parallel preparation; one shared integration)

| Workstream | Deliverables | Verification / exit criteria |
| --- | --- | --- |
| W1 — source and identity | Revision-pinned manifests for Python gateway, n8n 2.47.3 relay, PostgreSQL 17 migrations through 0015, worker and local model; adopted/excluded artifact decisions; secret-free configuration; dedicated numeric owner/chat/bot binding; no directly granted worker ledger DML | Digest verification, scoped grants, owner/foreign identity negative tests; owner-approved adoption decisions before runtime promotion |
| W2 — runtime and lifecycle | Fresh personal-beta database/volumes separate from any preserved Stage 1/2 evidence; one poller, one delivery worker, a single active host; startup dependency order, bounded health checks, graceful shutdown and fail-closed outbounds | Local synthetic dry run, duplicate worker rejection, restart/lease checks, no automatic replay of uncertain sends |
| W3 — dependable operation | Independently powered health observer and owner-visible alerts, overdue/quarantine reports, daily encrypted off-device backups on healthy media, restored-cluster verification and old-host fencing; define RPO/RTO and outage policy | Alert when Acer is unavailable, backup restore and exact history/receipt comparison; no unattended approval until these are demonstrated |
| W4 — functional slice | Owner-reviewed routine seed/proposals, no reminder by default unless requested, at-start/advance slot handling, edit/cancel/status, guarded historical Panchang | Offline/synthetic full user journey, bounded messages, no unauthorized writes or duplicate notifications |
| W5 — interface evolution | A transport-neutral interface contract and non-executable WhatsApp design note only | Static design review; Telegram behavior, schema and deployment unchanged |

Use one integration candidate and one coordinated validation matrix; do not
repeat previously accepted closed-lid, reboot or restore evidence except when a
new behavior invalidates it. Prefer ChatGPT Work for repository work; if a local
Docker/Windows/credential test is necessary, prepare **one consolidated Acer WSL
Codex task** with exact commands, pinned sources and a stop-on-failure policy.

## Two acceptance gates

### Gate 1 — Attended personal beta

Prerequisites: W1 source decisions recorded at exact revisions; W2/W4
synthetic validation passed; written rollback and manual-stop plan; bounded,
owner-approved dedicated bot, numeric owner-only recipient, allowed activities,
message budget and one named IST window. Start manually after interactive login
on AC power with physical attendance. Do not use an acceptance database,
credential, or prior one-use authorization. Confirm paired receipts and no silent,
duplicate or wrong-destination send. Stop on uncertain outcomes, identity
mismatch, unexpected egress or failed approval. Record sanitized evidence.

**Gate 1 permits only its specified attended operation, not an ongoing schedule
or unattended startup.** The operational monitoring/backup work may be developed
in parallel, but its unverified state must not be called reliable.

### Gate 2 — Unattended personal beta

Prerequisites: Gate 1 complete; verified independent monitor and out-of-band
owner alert (including complete laptop outage), approved routine encrypted
off-device backups and isolated restore on healthy media, active-host fencing,
single poller/worker, supervised startup and recovery policy, bounded backlog and
quarantine alert thresholds, secret custody and documented incident stop rules.
Request separate owner authorization for persistent personal messages and
startup. No automatic failover, blind resend or production/VPS activation.

A pass at Gate 2 authorizes only the exact personal-beta scope approved; general
lunar/festival scheduling, original source promotion, commercial use, `main`
merge and India VPS deployment have separate gates.

## WhatsApp future adapter — design only

Keep the business/domain APIs behind channel-independent request and response
objects: `ChannelIdentity(provider, external_user, destination, verified_owner)`,
`InboundIntent(request_id, received_at, language, text, buttons)`,
`ApprovalAction(action_id, revision, expiry, channel)`,
`OutboundNotification(slot_id, policy, channel, destination)`, and
`DeliveryEvidence(provider, external_message_id, accepted_at, uncertainty)`.
These are **conceptual contracts**, not approved database entities or code.

Design requirements:
1. One canonical schedule/approval ledger regardless of channel; authorize
   channel identity binding and any cross-channel approval explicitly.
2. Idempotent inbound actions and channel-scoped receipt identities; no duplicate
   delivery from Telegram and WhatsApp for the same occurrence unless the owner
   explicitly chooses multichannel delivery.
3. Provider-specific opt-in/template/session-window, consent, message billing,
   data retention and eligibility checks before writing a WhatsApp adapter.
4. Do not use unofficial WhatsApp Web automation, scrape sessions or expose the
   private bot credentials.
5. Review current Meta WhatsApp Business Platform terms and AI-assistant
   restrictions immediately before any real integration decision; eligibility is
   **not established** for this personal/general-purpose AI use case.

For this milestone, only document the conceptual adapter boundary. Do **not**
add WhatsApp libraries, migrations, channels or configuration switches to the
running application.

## Ordered execution and ownership

1. **Work / GitHub:** produce revision-pinned source disposition and beta-runtime
   inventory; reconcile digest-bound 2B decisions. Escalate only required
   authoritative artifact promotions.
2. **Work:** prepare one cohesive code/config candidate for W1/W2/W4 and the
   W3 monitoring/backup configuration, with disabled-by-default egress.
3. **Acer Codex when indispensable:** run one consolidated isolated integration
   task, verifying exact versions, PostgreSQL grants, signed n8n relay, simulated
   Telegram messages, backup/restore and external monitor paths. Report only
   sanitized PASS/FAIL results.
4. **Owner gate 1:** approve one finite attended test at the exact candidate
   revision, destination, time window and message/feature budget.
5. **Work + Acer:** incorporate any observed fixes; prove W3 and request separate
   gate 2 approval for routine unattended scheduling.
6. **After accepted Milestone 2 closure:** proceed to Adhyayan, Arogya,
   Atma-Chintan and Vittiya in the owner-approved sequence.

**No time estimate or percentage-complete claim is implied by this plan.**
