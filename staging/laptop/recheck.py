"""One fresh silent approval via the actual staging SDK, signed relay and database."""
import json
import sys
import subprocess
import time
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo

from control import PROJECT,STATE,compose,main as controller
from journey import query
from confirmation import snapshot,verify_confirmation


def inject(update):
    result=compose('exec','-T','gateway','python','/src/staging/laptop/service.py','inject',
                   input=json.dumps(update)+'\n',text=True,capture_output=True,timeout=60)
    return json.loads(result.stdout)


def main():
    if PROJECT!='dincharya-stage1-recheck':
        raise ValueError('Fresh diagnostic namespace required')
    sys.argv.insert(1,'status')
    controller()
    if snapshot(query)!=([0]*5,None):
        raise ValueError('Empty diagnostic ledger required')
    with (STATE/'confirmation.started').open('x') as record:
        record.write('reserved')
    actor={'id':101,'is_bot':False,'first_name':'Synthetic'}
    due=datetime.now(ZoneInfo('Asia/Kolkata'))+timedelta(minutes=10)
    msg={'message_id':1,'date':int(time.time()),'chat':{'id':101,'type':'private'},'from':actor,
         'text':f'Schedule Staging Silent on {due:%Y-%m-%d} at {due:%H:%M}; none'}
    preview=inject({'update_id':1,'message':msg})
    markup=preview['keyboard']
    if isinstance(markup,str):
        markup=json.loads(markup)
    ticket=markup['inline_keyboard'][0][0]['callback_data']
    if not ticket.startswith('lunar:confirm:') or len(preview['messages'])!=1:
        raise ValueError('Owner preview failed')
    def click(number,who):
        return inject({'update_id':number,'callback_query':{'id':str(number),'from':who,'data':ticket,
                      'message':msg,'chat_instance':'synthetic'}})
    if click(2,{**actor,'id':202})['messages'] or snapshot(query)!=([0]*5,None):
        raise ValueError('Unauthorized approval or preview write')
    try:
        result=click(3,actor)
    except (ValueError,OSError,subprocess.SubprocessError):
        result=None
    verify_confirmation(result,lambda:snapshot(query))
    committed=snapshot(query)
    # Only exercise idempotency after the original response AND ledger passed.
    verify_confirmation(click(4,actor),lambda:snapshot(query))
    if snapshot(query)!=committed:
        raise ValueError('Duplicate changed the committed control')
    check="import sqlite3; print(sqlite3.connect('file:/record/attempts.sqlite?mode=ro',uri=True).execute('SELECT count(*) FROM attempts').fetchone()[0])"
    if compose('exec','-T','worker','python','-c',check,capture_output=True,text=True).stdout.strip()!='0':
        raise ValueError('Unexpected recorder attempt')

if __name__=='__main__':
    main()
