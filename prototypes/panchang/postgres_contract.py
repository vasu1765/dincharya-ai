"""Opt-in synthetic PostgreSQL lunar API adapter. No connection on import/init.

The caller injects separate authenticated owner/calculator connection factories.
There is no actor ID, delivery method, retry loop, DSN or environment lookup.
Server migration 0006 is restricted to a disposable synthetic test database.
"""
from copy import deepcopy
import json
from uuid import UUID


class LunarStorageError(RuntimeError):
    """Sanitized failure: caller must inspect/replay with the SAME action ID."""


class SyntheticLunarPostgres:
    def __init__(self, connect):
        if not callable(connect):
            raise ValueError('Injected synthetic connection factory required')
        self._connect = connect

    def _call(self, statement, values):
        # Use driver parameters only. Context manager commits before returning;
        # any execution/commit failure is uncertain to the caller, never retried.
        try:
            with self._connect() as connection:
                row = connection.execute(statement, values).fetchone()
                if row is None:
                    raise ValueError('Missing API result')
                result = deepcopy(row[0])
            return result
        except Exception:
            raise LunarStorageError('Lunar transaction failed; inspect or replay the original action') from None

    @staticmethod
    def _uuid(value):
        if not isinstance(value, UUID):
            raise ValueError('UUID action/identity required')
        return value

    @staticmethod
    def _json(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)

    def propose_series(self, action, series, purpose, revision, rule):
        return self._call('SELECT lunar_api.propose_series(%s,%s,%s,%s,%s::jsonb)',
                          (self._uuid(action), self._uuid(series), purpose, revision, self._json(rule)))

    def record_calculation(self, action, series, revision, identity, profile, evidence, selection):
        return self._call('SELECT lunar_api.record_calculation(%s,%s,%s,%s::jsonb,%s,%s::jsonb,%s)',
                          (self._uuid(action), self._uuid(series), revision, self._json(identity), profile,
                           self._json(evidence), selection))

    def inspect_series(self, series):
        return self._call('SELECT lunar_api.inspect_series(%s)', (self._uuid(series),))

    def inspect_occurrence(self, occurrence):
        return self._call('SELECT lunar_api.inspect_occurrence(%s)', (self._uuid(occurrence),))

    def propose_occurrence(self, action, occurrence, operation, series_revision, occurrence_revision,
                           observation, desired):
        return self._call('SELECT lunar_api.propose_occurrence(%s,%s,%s,%s,%s,%s,%s::jsonb)',
                          (self._uuid(action), self._uuid(occurrence), operation, series_revision,
                           occurrence_revision, observation, self._json(desired)))

    def inspect_request(self, request):
        return self._call('SELECT lunar_api.inspect_request(%s)', (request,))

    def decide(self, action, request, decision, fingerprint, *, reviewed=False, force=False):
        return self._call('SELECT lunar_api.decide(%s,%s,%s,%s,%s,%s)',
                          (self._uuid(action), request, decision, fingerprint, reviewed, force))

    def propose_series_cancel(self, action, series, revision, manifest):
        return self._call('SELECT lunar_api.propose_series_cancel(%s,%s,%s,%s::jsonb)',
                          (self._uuid(action), self._uuid(series), revision, self._json(manifest)))
