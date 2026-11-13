"""Single-owner reminder adapters. Importing this module opens no connections."""
from datetime import datetime
import json
from uuid import UUID

from dincharya.reminders import Claim, NotAccepted


class PostgresReminders:
    """Use a fresh psycopg connection per operation and commit before returning."""

    def __init__(self, connect):
        self.connect = connect

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
                'FROM public.claim_occurrence_reminders(%s,%s)',
                (now, limit),
            ).fetchall()
        return [Claim(delivery_id, str(worker_token), payload)
                for delivery_id, worker_token, payload in rows]

    def finish(self, claim, outcome, now):
        with self.connect() as connection:
            row = connection.execute(
                'SELECT public.finish_occurrence_reminder(%s,%s,%s,%s)',
                (claim.delivery_id, UUID(claim.worker_token), outcome, now),
            ).fetchone()
        return row[0]


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
        if (response.status_code in {400, 401, 403, 404, 429}
                and body.get('ok') is False and body.get('error_code') == response.status_code):
            raise NotAccepted('Telegram rejected the reminder')
        result = body.get('result')
        if (response.status_code != 200 or body.get('ok') is not True
                or not isinstance(result, dict) or type(result.get('message_id')) is not int):
            raise RuntimeError('Telegram acknowledgement unavailable')


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
