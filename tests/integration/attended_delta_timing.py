"""Bounded timing helpers for the disposable attended acceptance only."""
import time


def wait_for_database_due(read_database_clock, due, *, sleep=time.sleep,
                          monotonic=time.monotonic, timeout=120.0,
                          max_lateness=55.0):
    """Wait against PostgreSQL's clock, staying inside the worker's due grace."""
    deadline = monotonic() + timeout
    while True:
        database_now = read_database_clock()
        lateness = (database_now - due).total_seconds()
        if lateness > max_lateness:
            raise TimeoutError("database due window elapsed")
        if lateness >= 0:
            return
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError("database clock did not reach appointment")
        sleep(min(0.25, remaining))
