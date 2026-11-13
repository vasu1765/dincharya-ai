"""Only Telegram network is simulated. Real SDK processes Update/CommandHandler."""
import json
from telegram import Update
from telegram.ext import Application
from telegram.request import BaseRequest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'telegram-gateway'))
from lunar_handlers import register_lunar


class OfflineBotAPI(BaseRequest):
    def __init__(self):self.messages=[];self.next_id=1
    async def initialize(self):pass
    async def shutdown(self):pass
    async def do_request(self,url,method,request_data=None,**kwargs):
        action=url.rsplit('/',1)[-1]
        if action=='getMe':result={'id':123456,'is_bot':True,'first_name':'Synthetic','username':'dincharya_offline_test_bot'}
        elif action=='sendMessage':
            args=request_data.parameters;self.messages.append(args['text']);self.next_id+=1
            result={'message_id':self.next_id,'date':1,'chat':{'id':101,'type':'private'},'text':args['text']}
        elif action=='deleteWebhook':result=True
        else:raise RuntimeError('Real Telegram method forbidden in isolated test')
        return 200,json.dumps({'ok':True,'result':result}).encode()


def build(commands,ticks,*,interval=1):
    request=OfflineBotAPI()
    app=Application.builder().token('123456:offline').request(request).get_updates_request(OfflineBotAPI()).build()
    register_lunar(app,101,commands,ticks,interval=interval)
    return app,request


def update(app,text,update_id,*,user=101,chat=101,chat_type='private',edited=False,is_bot=False):
    message={'message_id':update_id,'date':1,'chat':{'id':chat,'type':chat_type},
       'from':{'id':user,'is_bot':is_bot,'first_name':'Synthetic'},'text':text,
       'entities':[{'type':'bot_command','offset':0,'length':len(text.split()[0])}]}
    return Update.de_json({'update_id':update_id,'edited_message' if edited else 'message':message},app.bot)
