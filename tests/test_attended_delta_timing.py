from datetime import datetime, timedelta, timezone
from pathlib import Path
import importlib.util
import unittest


MODULE_PATH = Path(__file__).parent / "integration" / "attended_delta_timing.py"
SPEC = importlib.util.spec_from_file_location("attended_delta_timing", MODULE_PATH)
TIMING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TIMING)


class DatabaseDueWaitTests(unittest.TestCase):
    def test_waits_for_database_clock_not_host_clock(self):
        due = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
        samples = iter((due - timedelta(seconds=2), due - timedelta(seconds=1),
                        due + timedelta(milliseconds=20)))
        monotonic_now = [0.0]

        def sleep(seconds):
            monotonic_now[0] += seconds

        TIMING.wait_for_database_due(lambda: next(samples), due, sleep=sleep,
                                     monotonic=lambda: monotonic_now[0])
        self.assertGreater(monotonic_now[0], 0)
        self.assertLessEqual(monotonic_now[0], 1)

    def test_wait_is_bounded_if_database_clock_stalls(self):
        due = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
        monotonic_now = [0.0]

        def sleep(seconds):
            monotonic_now[0] += seconds

        with self.assertRaisesRegex(TimeoutError, "clock did not reach"):
            TIMING.wait_for_database_due(lambda: due - timedelta(seconds=10), due,
                                         sleep=sleep, monotonic=lambda: monotonic_now[0],
                                         timeout=0.6)
        self.assertLessEqual(monotonic_now[0], 0.6)

    def test_rejects_appointment_outside_worker_grace(self):
        due = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
        with self.assertRaisesRegex(TimeoutError, "due window elapsed"):
            TIMING.wait_for_database_due(lambda: due + timedelta(seconds=56), due)

    def test_rejects_mixed_naive_and_aware_clocks(self):
        due = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
        with self.assertRaises(TypeError):
            TIMING.wait_for_database_due(lambda: due.replace(tzinfo=None), due)


if __name__ == "__main__":
    unittest.main()
