# Cross-cluster recovery for partial approvals

Migration 0014 adds a restore fence to the isolated development database. It
leaves original requests, actions, approvals, observations and delivery receipts
in place. A backup can retain a request or calculation whose authorization
cannot be carried to a different cluster.

1. Keep both schedulers, relay and all worker processes stopped while switching
   clusters. Restore into a fresh disposable PostgreSQL instance. Recreate
   non-login executor groups and application logins independently with fresh
   credentials. Verify exact role names, intended memberships and owner subject
   against the scoped configuration. A matching name alone does not establish
   authority. Preserve original OIDs recorded in historical actions.
2. As the scoped synthetic bootstrap administrator, in the same transaction as
   the independently checked principal rebind, execute
   `SELECT lunar_private.fence_restored_pending();`. It records a new epoch,
   fences all restored pending schedule requests, and records unmaterialized
   lunar occurrences. A PostgreSQL trigger rejects updates or deletion of
   fenced requests. The app roles cannot run the fencing procedure or bypass
   the automatic projection wrapper. Complete the transaction before starting
   application connections.
3. Rotate command, tick and review signing material, restart the service with
   `development_restore_fence: true` and check owner identity and health.
   Old review buttons are discarded. New calculations use the restored epoch
   in their action IDs, retaining the same occurrence identity. The database
   holds restored partial automatic occurrences and leaves previously approved
   events and receipts intact.
4. Reopen a manual annual occurrence with `/lunar_year SERIES YEAR` and review
   the newly calculated date. For a restored partial automatic occurrence,
   the owner can review switching that rule to manual, open the year again,
   and confirm the new preview. A later explicit mode change can restore
   automatic behavior. A pending pre-restore action is kept as evidence and
   cannot be decided. Keep cases with no valid date or unresolved authority
   withheld. Never retry a quarantined delivery.

This procedure covers the defined synthetic database and known independently
recreated roles. It does not authorize rebind of arbitrary roles, alteration of
an original dump, production restoration or live use.
