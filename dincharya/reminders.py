"""Single-batch reminder worker with injected database/transport adapters.

Scheduling, identities, leases and retry decisions remain in PostgreSQL. This
module does not open connections, load credentials, poll Telegram or start a loop.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol, Sequence


@dataclass(frozen=True)
class Claim:
    delivery_id: int
    worker_token: str
    payload: Mapping[str, Any]


class Repository(Protocol):
    def claim(self, now: datetime, limit: int) -> Sequence[Claim]: ...
    def finish(self, claim: Claim, outcome: str, now: datetime) -> bool: ...


class Transport(Protocol):
    def send(self, payload: Mapping[str, Any]) -> None:
        """Return only on confirmed acceptance; otherwise raise."""


class NotAccepted(Exception):
    """The transport confirmed that no send was accepted; retry is safe."""


class DeliveryUncertain(RuntimeError):
    """No automatic resend is safe until the outcome is reconciled."""


def process_batch(repository: Repository, transport: Transport, clock, limit: int = 20) -> int:
    """Process claimed work once; never retry external I/O within this call."""
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('Batch limit must be between 1 and 100')
    claims = repository.claim(clock(), limit)

    def finish(claim, outcome):
        # A database failure can occur after Telegram accepted a send. Surface a
        # safe uncertainty signal and never retry the transport or acknowledgement.
        try:
            acknowledged = repository.finish(claim, outcome, clock())
        except Exception:
            raise DeliveryUncertain('Delivery outcome could not be persisted; reconciliation required') from None
        if not acknowledged:
            raise DeliveryUncertain('Delivery acknowledgement lease lost; reconciliation required') from None

    completed = 0
    for claim in claims:
        try:
            transport.send(claim.payload)
        except NotAccepted:
            finish(claim, 'not_accepted')
        except Exception:
            finish(claim, 'uncertain')
            raise DeliveryUncertain('Transport outcome unknown; automatic resend blocked') from None
        else:
            finish(claim, 'sent')
            completed += 1
    return completed
