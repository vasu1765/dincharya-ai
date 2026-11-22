# PR-stack integration review checkpoint — 2026-11-22

## Verified development integration and historical PR closeout — 22 November 2026

PR #17 was merged (not merely proposed) via history-preserving merge
`62421931de6dad60d389c7d8951cecf2fef1b68e`.
Parent 1: `7fc20d6c05e037b0ac3f01d11c5868b715476bd3`.
Parent 2: `4674c5d9ea3751272b8b1492849a324b2479f738`.

Acer Codex executed exactly two gateway preflight tests, both PASS, zero
skips. The unchanged isolated PostgreSQL 17 receipt migration 0015 script
returned exit 0 and the expected PASS line; disposable cleanup did not
change preserved Docker inventories. This closes the specific SQL acceptance
gate previously marked pending.

GitHub confirmed each remaining recorded historical head as an ancestor of
the integrated merge (zero commits behind). PR #4 was automatically marked
merged. PRs #5 and #7–#16 were closed **as superseded** by PR #17 after
independent ancestry and unchanged-head verification. No branch, commit,
review history or acceptance evidence was deleted. Earlier descriptions
below of a pending PR #17 merge and missing PG17 validation are historical
checkpoints superseded by this closeout.

### Pending source-adoption decisions

Repository-owned synthetic schema and migrations through 0015, inactive
native relay, bounded fixtures and source scanners remain approved for
isolated development only. Before personal beta, review exact source digests,
managed function grants without direct worker ledger DML, owner and bot
identity, single poller/worker, fail-closed delivery, backup and stop conditions.
A fresh, separately authorized real-message window is required.

Authoritative source/workflow promotion, current/published legacy workflow
replacement, historical Code execution, private-state adoption, broad
Panchang/festival rules, persistent deployment, unattended operation and
`main` merge are **not approved**. Use the digest-bound artifact table in
[M2B source adoption](M2B_SOURCE_ADOPTION.md) to obtain separate owner
dispositions.


## Consolidated development candidate — 22 November 2026

**Decision requested:** after the receipt SQL gate passes, merge this candidate with a merge commit into `development/m2g-telegram-integration` (reviewed target `7fc20d6c05e037b0ac3f01d11c5868b715476bd3`). One aggregate merge retains the twelve heads in their original history. Recheck the target and candidate pins first. Keep every original PR and branch available. Verify each head is an ancestor of the resulting target before deciding on any closure. Historical review comments [7076943222](https://github.com/vasu1765/dincharya-ai/pull/16#issuecomment-7076943222) and [7077006663](https://github.com/vasu1765/dincharya-ai/pull/16#issuecomment-7077006663) remain part of the evidence.

| PR | Verified head | Files changed | Status against recorded base | Proposed disposition |
|---|---|---:|---|---|
| #4 | `ac0dbb0ddc34bc376bf7d92c7e11e92952fc9f10` | 12 | Open draft, mergeable | Retain through aggregate merge and ancestry check |
| #5 | `f2753f9ff0f6f4221b3fc86c648936cb569151f3` | 15 | Open draft, mergeable | Retain through aggregate merge and ancestry check |
| #7 | `c378ab87813bbdb46d4f23f9c894dd48fc9b8ea0` | 14 | Open draft, mergeable | Retain through aggregate merge and ancestry check |
| #8 | `ac3f29f44336abb67db0755d3ff61ec3a2dfa3c8` | 12 | Open draft, mergeable | Retain through aggregate merge and ancestry check |
| #9 | `f37e2f593547ddfb030061981ec636bfdfa56a93` | 17 | Open draft, mergeable | Retain through aggregate merge and ancestry check |
| #10 | `29a4484fc4a1951be5e78a5fc1df754979c9434a` | 24 | Open draft, mergeable | Retain through aggregate merge and ancestry check |
| #11 | `2efa2685bca35f74c1b9038da9e693ceea9b4cc1` | 19 | Open draft, mergeable | Retain through aggregate merge and ancestry check |
| #12 | `e6a6743106ad887e2a725e2379cd80e6883d4b8e` | 12 | Open draft, mergeable | Retain through aggregate merge and ancestry check |
| #13 | `7b72a4aebb8232aa9e5e6fe14a9eddd8bbf086bb` | 3 | Open draft, mergeable | Retain through aggregate merge and ancestry check |
| #14 | `db4a8c75c7df3b0e815f36e486fc5d3127a916f1` | 13 | Open draft, mergeable | Retain through aggregate merge and ancestry check |
| #15 | `f4545a5b7cfb2871a4450ecc89a705862e89a9e1` | 16 | Open draft, mergeable | Retain through aggregate merge and ancestry check |
| #16 | `d4c1706a912e468974f033e22cf6785eeb47be0c` | 16 | Open draft, mergeable | Retain through aggregate merge and ancestry check |

Each base-to-head compare had zero commits behind. The correction branch was identical to 9e17254 before the integration change. Mergeability describes Git's conflict check only.

### Security and correctness review

| Severity | Finding and disposition |
|---|---|
| High, fixed in candidate | Python could acknowledge an absent transport receipt. The worker quarantines unconfirmed sends and its PostgreSQL adapter now also rejects receipt-less success before connecting. An actual paired receipt is required by success mocks. Rejection backoff, lease loss and uncertain delivery retain separate paths. |
| High, fixed in candidate; native validation pending | Both restricted Gregorian worker entry points could reach receipt-less success. Migration 0015 rejects that outcome, retains the scoped function owners and ACLs, and adds a slot constraint enforced on new writes. Previously applied migrations and historical null pairs remain intact. The historical public invoker API retains legacy behavior. Any beta worker must have scoped function execution and **no direct ledger DML**. |
| Medium, operating limit | The bounded signed relay and private runner bind the owner, destination, decision, revision and deadline. The general gateway also has a plain webhook route; keep it outside the attended beta. Signing authenticates the request. Durable action identity, review expiry and the database's transaction/lease checks supply replay and duplicate protection. |
| Medium, recovery and configuration | A shared database lock excludes a second worker on that cluster. It cannot fence a restored or independent host. Preserve sole bot custody, old-host fencing, fresh review for restored partial actions and the quarantine ledger. Restart or restore alone confers no approval. |
| Medium, provenance gate | Repository-owned synthetic schema, migrations, native inactive relay and test configuration can continue in isolated development. Before beta, verify deployed digests, managed grants and one-worker scope. The dispatcher, scanner, authoritative schema and workflow promotion require explicit artifact-level owner decisions. Current, published and historical legacy sources have distinct dispositions. Keep private Code bodies, old state, credentials and historical backups excluded. |
| Low, fixed | Two existing unit assertions modeled successful sends with a missing acknowledgement. The fixtures now require a real receipt on the success path; explicit negative coverage remains. |

The [artifact decision table](M2B_CYCLE7_DECISIONS.md) retains the individual digests. Add migration 0015 (SHA-256 `d1ccf7a8ff4e420c49a2f876e0405e409c00560ed146cf8ab5c5d0894b9bd67b`) and the updated private launcher (`1351e6ea3f755d2c877a8e72fb9a64247229a686ad7029640ab0adbc1a842b0d`) as development-only candidates. The historical inventory verified at `4f30e69fe7ea74fd128d650aac939bd4159c407d764068b229e989c0aa2552bd`. No authoritative promotion decision is recorded here.

### Verification and remaining gate

Work executed 5 receipt regressions, 27 reminder tests, 9 bounded acceptance tests and 6 reconciliation tests (47 passed). Two optional SDK/psycopg gateway preflight tests skipped. Explicit source checks, registry verification and shell syntax passed. Stage 1 signed native relay, PG17, duplicate suppression, quarantine and simulated receipts, plus Stage 2 lid-closed operation, the recovery-only continuation, encrypted USB transfer and independent restore remain prior evidence. Preserve the aborted first recovery, observer-tail gap and USB-health qualification in [the physical report](LAPTOP_STAGE2_RESULTS.md).

**One Acer WSL task.** Use a clean checkout of the reviewed candidate SHA and the previously accepted local PG17 image ID. From the repository root, set `REV` independently to the candidate pin and `PG` to that image ID. Using the existing gateway acceptance Python environment, run `python -B -m unittest discover -s tests -p test_reminder_gateway_preflight.py -v` and verify both tests execute. Then run `REV="$REV" PG="$PG" bash tests/integration/receipt_candidate.sh`. This creates one fresh networkless tmpfs cluster, applies the synthetic schema and migrations, checks both scoped worker APIs and receipt rows, and removes only that container. Record the exit status and PASS line on the integration PR. Work lacked PostgreSQL and Docker. Migration 0015 has no native PASS yet.

### Attended beta after development integration

1. Confirm source dispositions for the exact runtime, candidate migration ledger, isolated database and single polling/worker owner. Resolve the native gate before requesting a live window.
2. Obtain fresh authorization for an exact reviewed revision, dedicated test bot, numeric owner-only recipient, one 11-minute IST window and six outbound messages including one genuine reminder.
3. Execute the [bounded launcher](M2H_CYCLE7_PRIVATE_ACCEPTANCE.md) once within that authorization. It covers one historical query, one silent appointment and one at-start reminder with explicit confirmation. End on uncertainty, identity mismatch, extra traffic or receipt mismatch. Keep only scoped evidence. An ongoing personal schedule requires a separate approval.

## Historical initial correction checkpoint

## Scope and ancestry

Base: `d4c1706a912e468974f033e22cf6785eeb47be0c`, previously accepted PR #16.
The open drafts #4, #5 and #7–#16 form a linear dependent stack; the base is
51 commits ahead of `main`, zero behind. No force-push, main merge, branch
closure, deployment or prior acceptance replay is part of this review.

## Delivery-receipt finding and correction

`dincharya.reminders.process_batch` previously treated a transport returning
`None` as a successful send and finished the claim without a receipt. The
notification-slot SQL acknowledgement similarly permits a `sent` state with
null receipt fields. This is an untested edge-case risk, **not evidence** that
the accepted Stage 1 or Stage 2 paired receipts were missing.

The application-layer change now requires a valid `DeliveryReceipt` for every
successful transport return. Missing or malformed results are recorded as
`uncertain`, never `sent`, and cause `DeliveryUncertain` without an
automatic resend. Explicit `NotAccepted` outcomes remain retryable through
the existing bounded backoff. Storage-acknowledgement failures remain uncertain.

## Validation scope

Five new focused unit tests cover missing, malformed, valid, definitively
rejected and storage-failure outcomes. A standalone reproduction of the revised
worker function and test cases passed 5/5 offline. This is **not** a claim
that the full repository suite or native PostgreSQL/n8n integration was run
on the review branch. Those are pending integration gates.

No prior numbered migration was modified. SQL-level enforcement of the
receipt invariant and compatibility with legacy receipt-less pathways must be
reviewed separately before authoritative source promotion. Avoid a blanket
historical migration rewrite.

## Other observed boundaries

- `dincharya/lunar_service.py`: signed command envelope, 60-second bounded
  timestamp, distinct command/tick/review keys and isolated database logins.
- `dincharya/lunar_runtime.py`: rejects production DB names, uses owner-only
  configuration and requires explicit live approval and dedicated bot identity.
  It remains an acceptance runtime, not a general personal beta deployment.
- `workflows/m2g-lunar-acceptance.json`: inactive repository-owned Webhook
  and HTTP Request relay; standalone workflow import/publishing remains gated.
- `database/migrations/0011_synthetic_notification_slots.sql`: fixed
  search_path on SECURITY DEFINER functions, synthetic database checks and
  explicit role grants. Full privilege audit remains outstanding.
- `docs/M2B_SOURCE_ADOPTION.md`: owner artifact decisions still required
  before source promotion. Legacy private workflow bodies and Code-node
  history remain outside review.
- Stage 2 closed-lid, recovery-only, encrypted USB and independent restore
  evidence remains accepted within its documented scope, with observer-tail
  and USB-health qualifications retained.

## Integration recommendation

Run the repository's targeted reminder tests and source-safety scan, then one
small disposable database negative-case check if the SQL path needs adjustment.
Complete artifact-level source dispositions and review of gateway and database
privileges. Integrate sequentially into a development baseline only after a
reviewed decision. No live Telegram, automatic startup, production or main
merge follows from this branch.
