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
    completed = 0
    for claim in claims:
        try:
            transport.send(claim.payload)
        except NotAccepted:
            if not repository.finish(claim, 'not_accepted', clock()):
                raise DeliveryUncertain('Delivery lease was lost after rejection') from None
        except Exception:
            repository.finish(claim, 'uncertain', clock())
            raise DeliveryUncertain('Transport outcome unknown; automatic resend blocked') from None
        else:
            if not repository.finish(claim, 'sent', clock()):
                raise DeliveryUncertain('Accepted delivery lost its acknowledgement lease')
            completed += 1
    return completed
