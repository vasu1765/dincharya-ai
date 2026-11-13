"""Real SDK lunar commands. Identity comes ONLY from authenticated Telegram Update."""
import asyncio
import time
import logging
from telegram.ext import CommandHandler
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
