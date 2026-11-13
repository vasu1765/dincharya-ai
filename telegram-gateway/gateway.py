import asyncio
import logging
import os

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

load_dotenv()
TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
ALLOWED_ID = int(os.environ['TELEGRAM_ALLOWED_USER_ID'])
WEBHOOK = os.getenv('N8N_WEBHOOK_URL', 'http://localhost:5678/webhook/dincharya-chat')
logging.basicConfig(level=logging.INFO)
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

async def authorized(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id == ALLOWED_ID and update.effective_chat
        and update.effective_chat.type == "private")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await authorized(update):
        return
    await update.message.reply_text('Namaste! Dincharya AI is connected. Send me a message to test the local AI workflow.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await authorized(update) or not update.message or not update.message.text:
        return
    payload = {'message': update.message.text, 'user_id': update.effective_user.id, 'chat_id': update.effective_chat.id}
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(WEBHOOK, json=payload)
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
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    dsn = os.getenv('DINCHARYA_REMINDER_DSN')
    if dsn:
        from reminder_handlers import register_reminders

        register_reminders(app, dsn, TOKEN, ALLOWED_ID)
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
