"""Synthetic operator API; trusted identity comes only from the DB login.

No Telegram/transport dependency, resend/reset API, environment loading or
production enablement path exists here.
"""
from dataclasses import dataclass, field
import re
from uuid import UUID

from dincharya.reminders import DeliveryReceipt


@dataclass(frozen=True)
class ConfirmedDelivery:
    action_id: UUID
    delivery_id: int
    observation_version: str = field(repr=False)
    receipt: DeliveryReceipt = field(repr=False)
    evidence_ref: UUID = field(repr=False)
    reason: str = field(repr=False)
    authorization_ref: UUID = field(repr=False)
    confirmed: bool = False

    def __post_init__(self):
        if (any(not isinstance(value, UUID) for value in (self.action_id, self.evidence_ref, self.authorization_ref))
                or type(self.delivery_id) is not int or not 0 < self.delivery_id < 2**63
                or not isinstance(self.observation_version, str)
                or not re.fullmatch('[0-9a-f]{64}', self.observation_version)
                or not isinstance(self.receipt, DeliveryReceipt) or self.receipt.chat_id <= 0
                or not isinstance(self.reason, str) or not 1 <= len(self.reason.strip()) <= 500
                or any(ord(char)<32 or ord(char)==127 for char in self.reason)
                or self.confirmed is not True):
            raise ValueError('Explicit valid reconciliation authorization and evidence are required')


@dataclass(frozen=True)
class ResolutionResult:
    success: bool
    replayed: bool
    code: str


class OperatorReconciliation:
    def __init__(self, connect):
        # Factory must authenticate a dedicated operator DB login; no actor ID
        # argument, SET ROLE identity substitution or caller GUC is used.
        self.connect = connect

    def inspect(self, *, after_id=0, limit=20):
        if (type(after_id) is not int or not 0 <= after_id < 2**63
                or type(limit) is not int or not 1 <= limit <= 100):
            raise ValueError('Invalid inspection bounds')
        try:
            with self.connect() as connection:
                with connection.transaction():
                    connection.execute('SET TRANSACTION READ ONLY')
                    rows = connection.execute('SELECT * FROM reconcile_api.inspect_uncertain(%s,%s)',
                                              (after_id, limit)).fetchall()
            return rows
        except Exception:
            raise RuntimeError('Operator inspection unavailable') from None

    def record_confirmed(self, command):
        if not isinstance(command, ConfirmedDelivery):
            raise ValueError('Validated confirmed-delivery command required')
        try:
            with self.connect() as connection:
                row = connection.execute(
                    'SELECT success,replayed,code FROM reconcile_api.record_confirmed_delivered(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                    (command.action_id, command.delivery_id, command.observation_version,
                     command.receipt.chat_id, command.receipt.message_id, command.evidence_ref,
                     command.reason, command.authorization_ref, command.confirmed),
                ).fetchone()
            return ResolutionResult(*row)
        except Exception:
            # A commit acknowledgement can be lost. Never retry automatically;
            # the caller may inspect/replay the SAME action ID and exact command.
            raise RuntimeError('Reconciliation result unknown; inspect or replay the same action ID') from None
