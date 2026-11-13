"""Opt-in reminder commands and polling job for the existing Telegram gateway."""
import asyncio
from contextlib import closing
from datetime import datetime, timezone
import logging
from zoneinfo import ZoneInfo

import httpx
from telegram.ext import CommandHandler

from acceptance import decision_reply

from dincharya.reminder_adapters import PostgresReminders, TelegramReminders, parse_reminder
from dincharya.reminders import process_batch


def register_reminders(app, token, owner_id, *, dsn="", database=None):
    import psycopg

    def connect():
        return psycopg.connect(
            dsn, connect_timeout=5, options='-c statement_timeout=15000',
            **(database or {}),
        )

    with closing(connect()) as check:
        identity = ("current_database() = 'dincharya_app_test' AND session_user = 'synthetic_test' AND "
                    if database is not None else '')
        ready = check.execute(
            "SELECT " + identity + "(SELECT count(*) FROM public.application_migration_ledger "
            "WHERE version IN ('0001_gregorian_occurrences.sql', '0002_occurrence_reminders.sql', "
            "'0003_managed_legacy_boundary.sql', '0004_telegram_receipts.sql')) = 4 "
            "AND to_regprocedure('public.acknowledge_occurrence_reminder(bigint,uuid,text,timestamp with time zone,bigint,bigint)') IS NOT NULL"
        ).fetchone()[0]
        if ready is not True:
            raise ValueError('Reminder database identity or migrations could not be verified.')

    if isinstance(app.bot_data,dict):
        if app.bot_data.get('reminder_polling_owner'):raise ValueError('Duplicate reminder polling owner')
        app.bot_data['reminder_polling_owner']='gregorian'
    repository = PostgresReminders(connect)
    local_zone = ZoneInfo('Asia/Kolkata')
    logger = logging.getLogger(__name__)

    def authorized(update):
        chat, user = update.effective_chat, update.effective_user
        return chat and user and chat.type == 'private' and chat.id == user.id == owner_id

    async def propose(update, context):
        if not authorized(update):
            return
        try:
            when, title = parse_reminder(context.args, datetime.now(local_zone))
        except ValueError as error:
            await update.message.reply_text(str(error))
            return
        try:
            request_id = await asyncio.to_thread(repository.propose, owner_id, when, title)
        except Exception:
            logger.warning('Reminder proposal database operation failed')
            await update.message.reply_text('Could not confirm the reminder proposal.')
            return
        await update.message.reply_text(
            f'Proposal {request_id}: {title}\n{when:%Y-%m-%d %H:%M} Asia/Kolkata\n'
            f'To schedule it, send /approve_reminder {request_id}. '
            f'To discard it, send /reject_reminder {request_id}.'
        )

    async def decide(update, context, decision):
        if not authorized(update):
            return
        args = context.args
        if (len(args) != 1 or not args[0].isascii() or not args[0].isdigit()
                or len(args[0]) > 19 or not 1 <= int(args[0]) < 2**63):
            await update.message.reply_text(f'Use /{decision}_reminder followed by the proposal ID.')
            return
        try:
            success, message = await asyncio.to_thread(repository.decide, owner_id, int(args[0]), decision)
        except Exception:
            logger.warning('Reminder decision database operation failed')
            await update.message.reply_text('Could not confirm the reminder decision.')
            return
        await update.message.reply_text(decision_reply(success, message, decision))

    async def approve(update, context):
        await decide(update, context, 'approve')

    async def reject(update, context):
        await decide(update, context, 'reject')

    def tick():
        # A session lock covers claim, send and acknowledgement across gateway processes.
        with closing(connect()) as lease:
            lease.autocommit = True
            if not lease.execute('SELECT pg_try_advisory_lock(20261112,3)').fetchone()[0]:
                return
            with httpx.Client(timeout=10, trust_env=False) as client:
                transport = TelegramReminders(client.post, token, owner_id)
                process_batch(repository, transport, lambda: datetime.now(timezone.utc), limit=1)

    async def run_tick(context):
        try:
            await asyncio.to_thread(tick)
        except Exception:
            logger.warning('Reminder tick failed; inspect PostgreSQL delivery state')

    app.add_handler(CommandHandler('remind', propose))
    app.add_handler(CommandHandler('approve_reminder', approve))
    app.add_handler(CommandHandler('reject_reminder', reject))
    app.job_queue.run_repeating(run_tick, interval=15, first=1, job_kwargs={'max_instances': 1})
