"""Real SDK lunar commands. Identity comes ONLY from authenticated Telegram Update."""
import asyncio
import time
import logging
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters
from dincharya.lunar_intent import LUNAR, TITLE
from dincharya.lunar_service import envelope


class OrchestrationClient:
    def __init__(self,client,url,key):self.client=client;self.url=url;self.key=key
    def call(self,command,nonce):
        value,signature=envelope(self.key,command,nonce)
        response=self.client.post(self.url,json=value,headers={'x-dincharya-signature':signature})
        response.raise_for_status();return response.json()


def register_lunar(app,owner_id,commands,ticks,*,interval=15):
    if app.bot_data.get('reminder_polling_owner'):
        raise ValueError('Only one reminder polling owner may be registered')
    app.bot_data['reminder_polling_owner']='lunar'
    def authorized(update):
        return bool(update.message and update.effective_user and not update.effective_user.is_bot
            and update.effective_user.id==owner_id and update.effective_chat
            and update.effective_chat.type=='private' and update.effective_chat.id==owner_id)
    async def invoke(update,context,operation,kind=None):
        if not authorized(update):return
        args=context.args
        if len(args)!=1 or len(args[0])>3000:
            await update.message.reply_text('Use one fixture name, review token or occurrence ID as appropriate.');return
        if operation=='request':command={'operation':operation,'kind':kind,'fixture':args[0]}
        elif operation in ('status','cancel'):command={'operation':operation,'occurrence':args[0]}
        else:command={'operation':operation,'token':args[0]}
        try:
            result=await asyncio.to_thread(commands.call,command,str(update.update_id))
            reply=result.get('reply','Operation could not be confirmed; inspect status.')
        except Exception:reply='Operation could not be confirmed; inspect status before retrying.'
        for offset in range(0,len(reply),4000):
            await update.message.reply_text(reply[offset:offset+4000])
    async def birthday(u,c):await invoke(u,c,'request','birthday')
    async def anniversary(u,c):await invoke(u,c,'request','wedding_anniversary')
    async def rule(u,c):await invoke(u,c,'approve_rule')
    async def approve(u,c):await invoke(u,c,'approve')
    async def reject(u,c):await invoke(u,c,'reject')
    async def cancel(u,c):await invoke(u,c,'cancel')
    async def status(u,c):await invoke(u,c,'status')
    for name,callback in [('lunar_birthday',birthday),('lunar_anniversary',anniversary),('approve_lunar_rule',rule),
                          ('approve_lunar',approve),('reject_lunar',reject),('cancel_lunar',cancel),('lunar_status',status)]:
        app.add_handler(CommandHandler(name,callback))
    async def tick(context):
        try:await asyncio.to_thread(ticks.call,{'operation':'tick'},'tick-'+str(time.time_ns()))
        except Exception:pass  # DB uncertainty/history is authoritative; never retry here.
    app.job_queue.run_repeating(tick,interval=interval,first=interval,job_kwargs={'max_instances':1},name='dincharya-reminder-owner')

    async def error_handler(update,context):
        logging.getLogger(__name__).warning('Lunar gateway operation failed; inspect application state')
    app.add_error_handler(error_handler)


REVIEW_ACTION = re.compile(r"^lunar:(confirm|cancel):([A-Za-z0-9_-]{24})$")


class LunarTextFilter(filters.MessageFilter):
    def filter(self, message):
        return bool(message.text and LUNAR.search(TITLE.sub("", message.text)))


def register_lunar_previews(app, owner_id, commands):
    """Register the development interface against the signed orchestration client."""
    def authorized(update):
        user, chat = update.effective_user, update.effective_chat
        return bool(user and not user.is_bot and user.id == owner_id
                    and chat and chat.type == "private" and chat.id == owner_id)

    async def invoke(update, message, command):
        try:
            result = await asyncio.to_thread(commands.call, command, str(update.update_id))
            reply = result["reply"]
            review = result.get("review")
            keyboard = None
            if (result["status"] in {"rule_preview", "occurrence_preview", "cancellation_preview"}
                    and isinstance(review, str) and re.fullmatch(r"[A-Za-z0-9_-]{24}", review)):
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("Confirm / पुष्टि", callback_data=f"lunar:confirm:{review}"),
                    InlineKeyboardButton("Cancel / रद्द", callback_data=f"lunar:cancel:{review}"),
                ]])
            await message.reply_text(reply, reply_markup=keyboard)
        except Exception:
            await message.reply_text("Operation could not be confirmed. Check the same preview or status.")

    async def draft(update, context):
        if authorized(update) and update.message and update.message.text:
            raw = update.message.text
            if raw.startswith("/"):
                raw = raw.partition(" ")[2]
            await invoke(update, update.message, {"operation": "draft_lunar", "text": raw})

    async def decision(update, context):
        query = update.callback_query
        if not authorized(update) or not query or not query.message:
            return
        match = REVIEW_ACTION.fullmatch(query.data or "")
        if not match:
            return
        try:
            await query.answer()
        except Exception:
            # A callback acknowledgement can fail after Telegram delivers it.
            # Durable decision replay is handled by the approval service.
            pass
        operation = "confirm_lunar_draft" if match[1] == "confirm" else "cancel_lunar_draft"
        await invoke(update, query.message, {"operation": operation, "review": match[2]})

    async def annual_command(update, context):
        if not authorized(update) or not update.message:
            return
        name = update.message.text.split()[0].split("@")[0].lower()
        operations = {
            "/lunar_rules": ("list_lunar_annual", ("after",)),
            "/lunar_year": ("resume_lunar_annual", ("series", "year")),
            "/lunar_rule_status": ("status_lunar_annual", ("series",)),
            "/lunar_rule_cancel": ("cancel_lunar_annual", ("series",)),
            "/lunar_year_cancel": ("cancel_lunar_annual_occurrence", ("series", "occurrence")),
        }
        operation, fields = operations[name]
        args = context.args
        if name == "/lunar_rules" and not args:
            args = [None]
        if len(args) != len(fields) or any(value is not None and len(value) > 36 for value in args):
            await update.message.reply_text(f"Use {name} " + " ".join(fields))
            return
        command = dict(zip(fields, args), operation=operation)
        if "year" in command:
            if not re.fullmatch(r"[0-9]{4}", command["year"]):
                await update.message.reply_text("Use a four-digit civil year.")
                return
            command["year"] = int(command["year"])
        await invoke(update, update.message, command)

    app.add_handler(CommandHandler("lunar_preview", draft))
    app.add_handler(CommandHandler(
        ["lunar_rules", "lunar_year", "lunar_rule_status", "lunar_rule_cancel", "lunar_year_cancel"],
        annual_command,
    ))
    app.add_handler(CallbackQueryHandler(decision, pattern=REVIEW_ACTION))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & LunarTextFilter(), draft))
