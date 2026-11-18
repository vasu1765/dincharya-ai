"""Submit six synthetic owner-reviewed appointments and verify the bounded ledger."""
import argparse
from datetime import datetime, timedelta
import json
import time
from zoneinfo import ZoneInfo

from control import DB, STATE, compose, sql
from confirmation import snapshot, verify_confirmation

CASES=[('Silent',3),('First',5),('Second',20),('Outage',33),('Recovered',45),('uncertain',47)]

def submit(start):
    if query('SELECT count(*) FROM public.schedule_events')!='0' or (STATE/'journey.started').exists():
        raise ValueError('One use only')
    with (STATE/'journey.started').open('x') as f:
        f.write(start.isoformat())
    owner=dict(id=101,first_name='Synthetic',is_bot=False)
    chat=dict(id=101,type='private')
    def send(update):
        data=compose('exec','-T','gateway','python','/src/staging/laptop/service.py','inject',
                     input=json.dumps(update)+'\n',capture_output=True,text=True,timeout=60)
        return json.loads(data.stdout)
    for idx,(name,offset) in enumerate(CASES,1):
        due=start+timedelta(minutes=offset)
        policy='none' if name=='Silent' else 'at start'
        text=f'Schedule Staging {name} on {due:%Y-%m-%d} at {due:%H:%M}; {policy}'
        base=dict(date=int(time.time()),chat=chat,message_id=idx,text=text)
        preview=send({'update_id':idx*2,'message':dict(base,**{'from':owner})})
        markup=preview['keyboard']
        if isinstance(markup,str):
            markup=json.loads(markup)
        action=markup['inline_keyboard'][0][0]['callback_data']
        if not action.startswith('lunar:confirm:'):
            raise ValueError('Expected review')
        result=send({'update_id':idx*2+1,'callback_query':{'id':str(idx),'from':owner,'data':action,
                            'message':base,'chat_instance':'synthetic'}})
        if idx==1:
            verify_confirmation(result,lambda:snapshot(query))
        elif len(result['messages'])!=1 or not result['messages'][0].startswith('Rule approved. ID ') or result['keyboard']:
            raise ValueError('Review incomplete')
    count=query("SELECT count(*) FROM public.schedule_events")
    if count!='6':
        raise ValueError('Approval count mismatch')

def query(statement):
    return sql('psql','-XAtq','-U','synthetic_test','-d',DB,'-c',statement,capture_output=True,text=True).stdout.strip()

def verify():
    actual=query("SELECT e.title,s.status,s.attempts,s.telegram_chat_id,s.telegram_message_id FROM public.schedule_events e LEFT JOIN lunar_private.notification_slot s ON e.id=s.event_id ORDER BY e.title").splitlines()
    expected=set()
    receipts=set()
    for line in actual:
        title,status,attempts,owner,receipt=line.split('|')
        if title=='Staging Silent':
            assert (status,attempts,owner,receipt)==('','','','')
        elif title=='Staging uncertain':
            assert (status,attempts,owner,receipt)==('uncertain','1','','')
        else:
            assert (status,attempts,owner)==('sent','1','101') and int(receipt)>0
            receipts.add(int(receipt))
        expected.add(title)
    if len(actual)!=6 or expected!={'Staging '+name for name,_ in CASES} or len(receipts)!=4:
        raise ValueError('Unexpected ledger')
    code="import sqlite3; print(sqlite3.connect('file:/record/attempts.sqlite?mode=ro',uri=True).execute('select count(*),sum(uncertain) from attempts').fetchone())"
    if compose('exec','-T','worker','python','-c',code,capture_output=True,text=True).stdout.strip()!='(5, 1)':
        raise ValueError('Unexpected transport count')
    print('PASS four paired receipts, zero silent attempts, one quarantined attempt')

if __name__=='__main__':
    from control import main as control
    import sys
    if not __debug__:
        raise SystemExit('Run with assertions enabled')
    action=sys.argv.pop(1)
    if action not in ('submit','verify'):
        raise SystemExit('Choose submit or verify')
    sys.argv.insert(1,'status')
    control()
    if action=='submit':
        submit(datetime.now(ZoneInfo('Asia/Kolkata')).replace(second=0,microsecond=0))
    else:
        verify()
