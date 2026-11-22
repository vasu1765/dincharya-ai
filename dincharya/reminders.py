"""Single-batch reminder worker with injected database/transport adapters.

Scheduling, identities, leases and retry decisions remain in PostgreSQL. This
module does not open connections, load credentials, poll Telegram or start a loop.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Protocol, Sequence


@dataclass(frozen=True)
class Claim:
    delivery_id: int
    worker_token: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class DeliveryReceipt:
    chat_id: int = field(repr=False)
    message_id: int = field(repr=False)

    def __post_init__(self):
        if (type(self.chat_id) is not int or not -(2**63) <= self.chat_id < 2**63 or self.chat_id == 0
                or type(self.message_id) is not int or not 0 < self.message_id < 2**63):
            raise ValueError('Invalid delivery receipt')


class Repository(Protocol):
    def claim(self, now: datetime, limit: int) -> Sequence[Claim]: ...
    def finish(self, claim: Claim, outcome: str, now: datetime, *, receipt: DeliveryReceipt | None = None) -> bool: ...


class Transport(Protocol):
    def send(self, payload: Mapping[str, Any]) -> DeliveryReceipt | None:
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

    def finish(claim, outcome, receipt=None):
        # A database failure can occur after Telegram accepted a send. Surface a
        # safe uncertainty signal and never retry the transport or acknowledgement.
        try:
            if receipt is None:
                acknowledged = repository.finish(claim, outcome, clock())
            else:
                acknowledged = repository.finish(claim, outcome, clock(), receipt=receipt)
        except Exception:
            raise DeliveryUncertain('Delivery outcome could not be persisted; reconciliation required') from None
        if not acknowledged:
            raise DeliveryUncertain('Delivery acknowledgement lease lost; reconciliation required') from None

    completed = 0
    for claim in claims:
        try:
            receipt = transport.send(claim.payload)
            # A missing receipt does not establish a confirmed external send.
            # Never turn a transport's None return into a sent ledger row.
            if not isinstance(receipt, DeliveryReceipt):
                raise RuntimeError('Transport acknowledgement absent or invalid')
        except NotAccepted:
            finish(claim, 'not_accepted')
        except Exception:
            finish(claim, 'uncertain')
            raise DeliveryUncertain('Transport outcome unknown; automatic resend blocked') from None
        else:
            finish(claim, 'sent', receipt)
            completed += 1
    return completed
