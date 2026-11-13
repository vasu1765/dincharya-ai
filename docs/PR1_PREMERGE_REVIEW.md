# PR #1 pre-merge review — 2026-11-13

Reviewed `main` (`b80a91d8`) against development head
`43ad6530fbb66ff89b94c7361d3c21fc1c2bba56`, including the complete PR diff and
the worker/SQL retry and quarantine contracts.

## Mergeability

GitHub returned `mergeable=MERGEABLE`, `mergeStateStatus=CLEAN`, `isDraft=true`,
empty review decision and no status checks. Main is an ancestor of the local
development head. No conflict or failing check was observed. Draft status prevents
merging; no ready-for-review transition or merge was performed.

## Blocking finding and local fix

HTTP 429 was classified as ordinary `NotAccepted`. SQL retries after 30, 60, 120
and 240 seconds and marks the fifth rejection dead. Telegram's
[retry_after](https://core.telegram.org/bots/api#responseparameters) specifies a
minimum flood-control wait, which the adapter discarded. A 3600-second wait could
therefore trigger four premature retries and exhaust the attempt budget.

Fixed locally by excluding every HTTP 429 from automatic retries and using the
existing quarantine path. This deliberately uses `uncertain` as a manual-hold
state even for confirmed flood-control rejection. No sleep under a live lease,
schema change, mutation of checksummed migrations or new retry loop was added.
Automatic flood-control recovery remains follow-up work requiring durable wait
state. A human must respect Telegram's wait before recovery; quarantine is not
successful delivery. Other matching 400/401/403/404 failures retain the bounded
rejection policy; timeout, 5xx, malformed acknowledgement and lease loss preserve
the existing no-blind-resend boundary.

Regression test failed on the previous adapter, then passed with the fix.
Tests cover long/short/malformed/missing cooldown values, quarantine persistence
through the repository API and one transport call, plus unchanged handling of
other definitive rejections. All **15** focused reminder tests passed:

```bash
python3 -B -m unittest discover -s tests -p 'test_reminder_*.py' -v
```

No additional critical correctness, security or regression issue found in the
changed adapters, owner checks, command dispatch, acceptance configuration,
dependency declarations, tests and secret-entry helper. Existing broader 2D/2E,
least-privilege, reconciliation and production-readiness gaps remain outside this
development PR. This review is not production authorization.

## Acceptance and disposition

Live success remains recorded against runtime source `aa05dd2` and committed in
`43ad653`; the 429 fix was tested offline only. No Telegram call/live test,
credential access, Docker test, production access, deployment or merge was made
during this review. PR acceptance checkboxes now reflect the successful evidence.

The current remote head still contains the 429 bug until the local fix is
committed/pushed. Git metadata is read-only in this sandbox, so the owner must
execute the explicit commands in HANDOFF.md. After that fix is pushed and reviewed,
PR #1 is suitable for final owner merge approval as development source. It must
also leave draft status before merging. No other merge blocker was found.
