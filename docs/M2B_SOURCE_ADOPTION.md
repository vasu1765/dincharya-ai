# Milestone 2B source adoption review

The owner approved establishing a new process on 17 November 2026. The package
covers the repository-owned synthetic schema, ordered migrations, test configuration,
native relay and security-sensitive dispatcher and source scanner. It is awaiting
artifact-level review. This package preserves the historical evidence in Git and
makes no claim about the contents of the unavailable original manifest.

## Review package

See the [Cycle 7 artifact-by-artifact disposition package](M2B_CYCLE7_DECISIONS.md)
for the current review. It retains the Cycle 6 manifest and separately lists the
new recovery sources by digest.

Run from the repository root.

```bash
python3 scripts/review-source-adoption.py --verify
```

The [inventory](m2b-repository-review.json) identifies each proposed artifact by
path, repository, Git blob, SHA-256, purpose, category, scope and disposition.
The checkpoint is the parent development commit. The blob and SHA-256 identify
the candidate bytes, including changes on the review branch. The verifier reads
only the registered repository paths. It refuses symlinks and changed artifact
bytes. The native relay has two reviewed node classes, Webhook and HTTP Request.
Receipt of a native relay definition does not authorize its deployment or the
execution of historical Code nodes.

Prior extraction reports record four current workflows, 94 historical versions,
two structural candidates and seven Code bodies. Current and published workflow
identities remain separate, even where bodies appeared to match. The package
archives the evidence and identifies missing or excluded inputs explicitly.
Unknown historical versions and checksums remain null. [Prior extraction evidence](extracted-workflow-analysis.md)

| Review area | Evidence available | Compatibility or migration risk |
| --- | --- | --- |
| PostgreSQL schema and migrations | Invented fixture and all numbered migrations have distinct digests | Cycle 6 passed exact-schema testing. Cycle 7 separately passed the focused same-database test for the 0014 fence. |
| Native n8n definition | Repository-owned inactive relay, reconstructed on n8n 2.47.3 | Local harness binds only the isolated HTTP or Unix socket destination. Verify retention and logging before operational use. |
| Current and published original workflows | Prior structural evidence and version counts | Review each version under separately scoped authorization before any replacement or adoption. Preserve external state. |
| Historical workflows and Code nodes | Inventory-level evidence only | Historical execution is excluded. Preserve source and state if separately approved for read or archival. |
| Application configuration and security-sensitive code | Pinned test configuration, signer dispatch and source scanner | Review effective grants, exact socket routing, test defaults and disallowed runtime settings in the intended target. |

## Independent review and decision record

1. The author proposes registered repository artifacts with
   `python3 scripts/review-source-adoption.py --propose-at COMMIT`. Commit the
   resulting inventory with the exact base commit, changed bytes, discrepancies
   and reconstruction report. Any new private input requires its own explicit
   file and operation authorization before it can be proposed.
2. A reviewer verifies the manifest and independently reviews the schema, workflow
   wiring, configuration and privileged code. Run [the disposable reconstruction](M2H_CYCLE6_HISTORICAL.md#reproduce).
   Record reconstruction commands, runtime versions, compatibility results and
   any intentional exclusions in the draft. The verifier checks artifact identity
   and structure. Reviewers assess the actual content and behavior.
3. The owner records decisions in the review PR, identifying the output SHA-256
   from `--verify`. A subsequent PR can add `docs/m2b-owner-decisions.json` with
   `version` set to 1, `package_sha256`, the GitHub review URL in `review`, and
   one object per candidate in `decisions`. Each object has `path`, `sha256`,
   `status` and `reason`. Status is `adopted`, `replaced`, `archived`,
   `excluded` or `awaiting_review`. A replacement decision records the reviewed
   replacement path or package in its reason. Check the decision record with
   `--verify-decisions` and confirm the approving reviewer in GitHub. The
   verifier checks the binding and format. GitHub supplies the approval audit.
4. A separately reviewed promotion change selects sources adopted for a named
   scope. Preserve the package, decision record and previous manifests in Git.
   Production promotion, private inputs and any historical Code execution
   require specific authorization.

Issue #6 tracks artifact approval and exact-schema compatibility. The original
Cycle 4 schema-only acceptance remains scoped to that archived checkpoint.
