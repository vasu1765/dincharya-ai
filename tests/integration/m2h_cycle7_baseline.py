"""Focused Cycle 7 acceptance on the previously authorized schema-only baseline."""
import asyncio
from pathlib import Path

from m2h_cycle6_baseline import ExactRunner, main
from m2h_cycle7 import civil_journey, recovery_seed
from dincharya.lunar_service import envelope


class ReleaseRunner(ExactRunner):
    label = "Cycle 7"
    migrations = (*ExactRunner.migrations, "0014_synthetic_restore_fence.sql")
    server_script = Path(__file__).name

    def configure_service(self):
        super().configure_service()
        self.config["development_restore_fence"] = True

    async def checks(self, service, relay, admin, role_info):
        self.checkpoint("Civil SDK to delivery receipts")
        await asyncio.to_thread(civil_journey, service, relay, admin)
        self.checkpoint("Recovery fence on authorized schema")
        verify = await asyncio.to_thread(recovery_seed, service, relay, admin, self.year)
        # Same disposable database for the exact-schema compatibility check.
        # Cross-cluster role recreation is a separate Cycle 7 synthetic run.
        self.stop_service()
        admin.execute("SELECT lunar_private.fence_restored_pending()")
        rebound = relay.restart_service()
        value, signature = envelope(rebound.tick_key, {"operation": "project_tick"}, "exact-fence")
        assert (await asyncio.to_thread(relay.forward, value, signature))["status"] == "projected"
        await asyncio.to_thread(verify, admin, self.config, rebound)


if __name__ == "__main__":
    try:
        main(ReleaseRunner)
    except Exception:
        raise SystemExit("Cycle 7 exact baseline acceptance failed. Private runtime details suppressed.") from None
