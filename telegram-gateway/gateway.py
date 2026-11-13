import logging
import os
import sys

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

async def authorized(update: Update, owner_id) -> bool:
    return bool(update.effective_user and update.effective_user.id == owner_id and update.effective_chat
        and update.effective_chat.type == "private")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await authorized(update, context.bot_data['owner_id']):
        return
    await update.message.reply_text('Namaste! Dincharya AI is connected. Send me a message to test the local AI workflow.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await authorized(update, context.bot_data['owner_id']) or not update.message or not update.message.text:
        return
    payload = {'message': update.message.text, 'user_id': update.effective_user.id, 'chat_id': update.effective_chat.id}
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(context.bot_data['webhook'], json=payload)
            response.raise_for_status()
            data = response.json()
        reply = data.get('reply') if isinstance(data, dict) else None
        if not isinstance(reply, str) or not reply.strip():
            raise ValueError('n8n response did not contain a nonempty reply field')
        for i in range(0, len(reply), 4000):
            await update.message.reply_text(reply[i:i+4000])
    except Exception:
        logger.exception('Workflow request failed')
        await update.message.reply_text('The AI workflow is unavailable. Check the gateway and n8n logs.')


def main():
    if sys.argv[1:] == ['--acceptance']:
        from acceptance import load_acceptance
        from reminder_handlers import register_reminders

        try:
            config = load_acceptance(os.environ)
        except ValueError as error:
            raise SystemExit(str(error)) from None
        app = Application.builder().token(config.token).build()
        try:
            register_reminders(app, config.token, config.owner_id, database=config.database)
        except Exception:
            raise SystemExit('Could not verify the disposable reminder database.') from None
    elif not sys.argv[1:]:
        load_dotenv()
        token = os.environ['TELEGRAM_BOT_TOKEN']
        owner_id = int(os.environ['TELEGRAM_ALLOWED_USER_ID'])
        app = Application.builder().token(token).build()
        app.bot_data['owner_id'] = owner_id
        app.bot_data['webhook'] = os.getenv('N8N_WEBHOOK_URL', 'http://localhost:5678/webhook/dincharya-chat')
        app.add_handler(CommandHandler('start', start))
        dsn = os.getenv('DINCHARYA_REMINDER_DSN')
        if dsn:
            from reminder_handlers import register_reminders

            try:
                register_reminders(app, token, owner_id, dsn=dsn)
            except Exception:
                raise SystemExit('Could not verify the reminder database migrations.') from None
        app.add_handler(MessageHandler(filters.TEXT, handle_message))
    else:
        raise SystemExit('Usage: gateway.py [--acceptance]')
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
