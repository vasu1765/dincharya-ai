"""Single-owner reminder adapters. Importing this module opens no connections."""
from dataclasses import dataclass, field
from datetime import date, datetime
import json
from uuid import UUID

from dincharya.reminders import Claim, DeliveryReceipt, NotAccepted


@dataclass(frozen=True)
class QuarantinedReminder:
    delivery_id: int
    event_id: int
    occurrence_date: date
    attempts: int
    due_at: datetime | None
    claimed_at: datetime | None
    has_receipt: bool
    observation_version: str = field(repr=False)


class PostgresReminders:
    """Use a fresh psycopg connection per operation and commit before returning."""

    def __init__(self, connect, *, restricted_worker=False):
        if type(restricted_worker) is not bool:
            raise ValueError('Invalid worker API selection')
        self.connect = connect
        self.worker_schema = 'reminder_worker_api' if restricted_worker else 'public'

    def propose(self, user_id, when, title):
        data = {
            'title': title,
            'start_time': when.strftime('%H:%M'),
            'end_time': None,
            'timezone': 'Asia/Kolkata',
            'recurrence_rule': {
                'calendar_system': 'gregorian',
                'frequency': 'once',
                'interval_count': 1,
                'start_date': when.date().isoformat(),
            },
        }
        with self.connect() as connection:
            row = connection.execute(
                "SELECT public.propose_gregorian_change('add','series',NULL,NULL,%s::jsonb,%s)",
                (json.dumps(data), user_id),
            ).fetchone()
        return row[0]

    def decide(self, user_id, request_id, decision):
        with self.connect() as connection:
            row = connection.execute(
                'SELECT success, message FROM public.decide_gregorian_change(%s,%s,%s)',
                (request_id, user_id, decision),
            ).fetchone()
        return row

    def claim(self, now, limit):
        with self.connect() as connection:
            rows = connection.execute(
                'SELECT delivery_id, worker_token, payload '
                f'FROM {self.worker_schema}.claim_occurrence_reminders(%s,%s)',
                (now, limit),
            ).fetchall()
        return [Claim(delivery_id, str(worker_token), payload)
                for delivery_id, worker_token, payload in rows]

    def finish(self, claim, outcome, now, *, receipt=None):
        if receipt is not None and (outcome != 'sent' or not isinstance(receipt, DeliveryReceipt)):
            raise ValueError('Invalid delivery receipt')
        with self.connect() as connection:
            if receipt is None:
                row = connection.execute(
                    f'SELECT {self.worker_schema}.finish_occurrence_reminder(%s,%s,%s,%s)',
                    (claim.delivery_id, UUID(claim.worker_token), outcome, now),
                ).fetchone()
            else:
                row = connection.execute(
                    f'SELECT {self.worker_schema}.acknowledge_occurrence_reminder(%s,%s,%s,%s,%s,%s)',
                    (claim.delivery_id, UUID(claim.worker_token), outcome, now,
                     receipt.chat_id, receipt.message_id),
                ).fetchone()
        return row[0]

    def list_quarantined(self, *, after_id=0, limit=20):
        """Read bounded metadata for reconciliation; never release or resend work.

        Page by the last returned delivery_id. No titles, payloads, chat IDs,
        worker tokens or arbitrary transport error text leave the database.
        """
        if (type(limit) is not int or not 1 <= limit <= 100
                or type(after_id) is not int or not 0 <= after_id < 2**63):
            raise ValueError('Invalid quarantine page bounds')
        with self.connect() as connection:
            # Explicit transaction also enforces these settings on autocommit clients.
            with connection.transaction():
                connection.execute('SET TRANSACTION READ ONLY')
                connection.execute("SET LOCAL TIME ZONE 'UTC'")
                rows = connection.execute(
                    'SELECT d.id,d.event_id,d.occurrence_date,d.attempts,d.due_at,d.claimed_at, '
                    '(d.telegram_chat_id IS NOT NULL AND d.telegram_message_id IS NOT NULL), '
                    "encode(sha256(convert_to(to_jsonb(d)::text,'UTF8')),'hex') "
                    'FROM public.reminder_deliveries d '
                    "WHERE d.managed_by='m2e' AND d.status='uncertain' AND d.id>%s "
                    'ORDER BY d.id LIMIT %s', (after_id, limit),
                ).fetchall()
        return [QuarantinedReminder(*row) for row in rows]


class TelegramReminders:
    """Send plain text to the configured private chat via the Bot API."""

    def __init__(self, post, token, owner_id):
        self.post = post
        self.url = f'https://api.telegram.org/bot{token}/sendMessage'
        self.owner_id = owner_id

    def send(self, payload):
        text = f"Reminder: {payload['title']}\n{payload['occurrence_date']} {payload['start_time']} ({payload['timezone']})"
        try:
            response = self.post(self.url, json={'chat_id': self.owner_id, 'text': text})
            body = response.json()
        except Exception:
            raise RuntimeError('Telegram acknowledgement unavailable') from None
        if not isinstance(body, dict):
            raise RuntimeError('Unexpected Telegram response')
        # SQL's bounded rejection backoff cannot persist Telegram's retry_after.
        # Quarantine flood-control responses rather than retrying too early or
        # sleeping with a live lease. This also fails closed on malformed 429s.
        if response.status_code == 429:
            raise RuntimeError('Telegram rate limit requires manual recovery')
        if (response.status_code in {400, 401, 403, 404}
                and body.get('ok') is False and body.get('error_code') == response.status_code):
            raise NotAccepted('Telegram rejected the reminder')
        result = body.get('result')
        if (response.status_code != 200 or body.get('ok') is not True
                or not isinstance(result, dict) or type(result.get('message_id')) is not int):
            raise RuntimeError('Telegram acknowledgement unavailable')
        chat = result.get('chat')
        if (not isinstance(chat, dict) or type(chat.get('id')) is not int
                or chat['id'] != self.owner_id):
            raise RuntimeError('Telegram destination acknowledgement unavailable')
        try:
            return DeliveryReceipt(chat['id'], result['message_id'])
        except ValueError:
            raise RuntimeError('Telegram acknowledgement unavailable') from None


def parse_reminder(arguments, now):
    """Parse a future Asia/Kolkata minute and a short plain-text title."""
    if len(arguments) < 3:
        raise ValueError('Use /remind YYYY-MM-DD HH:MM title (Asia/Kolkata).')
    raw = ' '.join(arguments[:2])
    try:
        when = datetime.strptime(raw, '%Y-%m-%d %H:%M').replace(tzinfo=now.tzinfo)
    except ValueError:
        raise ValueError('Use /remind YYYY-MM-DD HH:MM title (Asia/Kolkata).') from None
    title = ' '.join(arguments[2:])
    if when.strftime('%Y-%m-%d %H:%M') != raw or when <= now or not 1 <= len(title) <= 200:
        raise ValueError('Enter a future date and time and a title of up to 200 characters.')
    return when, title
