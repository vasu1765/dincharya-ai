"""Acceptance-only lunar application. No Docker, psql, astronomy or polling loop."""
from contextlib import closing
from datetime import date, datetime, timezone
import base64
import hashlib
import hmac
import json
import re
import os
import time
from uuid import UUID, uuid5

from prototypes.panchang.postgres_contract import SyntheticLunarPostgres, LunarStorageError
from dincharya.reminder_adapters import PostgresReminders, TelegramReminders
from dincharya.reminders import process_batch, DeliveryUncertain

NAMESPACE=UUID('8c492eb7-bad2-4868-aa67-2a042e0bb312')
DEVELOPMENT_OPERATIONS = frozenset({
    "draft_lunar", "confirm_lunar_draft", "cancel_lunar_draft",
    "list_lunar_annual", "resume_lunar_annual", "cancel_lunar_annual",
    "status_lunar_annual", "cancel_lunar_annual_occurrence",
})


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def sign(key,domain,value):
    return hmac.new(key.encode(),domain.encode()+b'\0'+canonical(value).encode(),hashlib.sha256).hexdigest()


def envelope(key,command,nonce,clock=time.time):
    value={'command':command,'nonce':str(nonce),'timestamp':int(clock())}
    return value,sign(key,'command',value)


class ReviewTokens:
    def __init__(self,key,clock=time.time):self.key=key;self.clock=clock
    def issue(self,data):
        value={**data,'expires':int(self.clock())+1800}
        encoded=base64.urlsafe_b64encode(canonical(value).encode()).decode().rstrip('=')
        return encoded+'.'+sign(self.key,'review',value)
    def read(self,token):
        if not isinstance(token,str) or len(token)>3000:raise ValueError('Invalid review')
        encoded,signature=token.split('.')
        value=json.loads(base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4)))
        if not hmac.compare_digest(signature,sign(self.key,'review',value)) or value['expires']<self.clock():
            raise ValueError('Expired or changed review')
        return value


def connection_factory(settings):
    """Explicit real psycopg connections, trusted login pinned on every operation."""
    allowed={'host','port','dbname','user','password'}
    if (set(settings)-allowed or settings.get('dbname')!='dincharya_app_test'
            or not settings.get('user') or not settings.get('password')
            or not (str(settings.get('host','')).startswith('/') or
                    settings.get('host')=='127.0.0.1' and int(settings.get('port',0)) not in (0,5432))):
        raise ValueError('Explicit isolated database configuration required')
    def connect():
        if any(k.startswith('PG') for k in os.environ):raise ValueError('Clear inherited PostgreSQL settings')
        import psycopg
        conn=psycopg.connect(**settings,passfile='/dev/null',sslmode='disable',connect_timeout=5,
             options='-c statement_timeout=15000 -c timezone=UTC -c datestyle=ISO,YMD')
        try:
            identity=conn.execute('SELECT current_database(),session_user').fetchone()
            if identity!=('dincharya_app_test',settings['user']):raise ValueError('Database identity mismatch')
            dangerous=conn.execute("SELECT rolsuper OR rolcreaterole OR rolcreatedb OR rolbypassrls OR "
                "pg_has_role(session_user,'dincharya_lunar_executor','MEMBER') OR "
                "pg_has_role(session_user,'dincharya_worker_executor','MEMBER') OR "
                "pg_has_role(session_user,'dincharya_reconcile_executor','MEMBER') "
                "FROM pg_roles WHERE rolname=session_user").fetchone()[0]
            if dangerous:raise ValueError('Privileged application login rejected')
            return conn
        except Exception:
            conn.close();raise
    return connect


class FixtureCatalog:
    def __init__(self,value):
        if value.get('synthetic') is not True or value.get('astronomy_enabled') is not False:
            raise ValueError('Only explicitly synthetic calendar fixtures are supported')
        self.fixtures=value['fixtures']
    def get(self,name,kind=None):
        fixture=self.fixtures[name]
        if kind is not None and fixture['purpose']!=kind:raise ValueError('Fixture purpose mismatch')
        return fixture


class LunarService:
    def __init__(self,owner_connect,calculator_connect,worker_connect,catalog,command_key,tick_key,review_key,*,transport=None,
                 development_calendar=None, development_profile=None):
        keys=(command_key,tick_key,review_key)
        if len(set(keys))!=3 or not all(isinstance(k,str) and re.fullmatch(r'[a-f0-9]{64}',k) for k in keys):
            raise ValueError('Distinct strong application keys required')
        self.owner=SyntheticLunarPostgres(owner_connect);self.calculator=SyntheticLunarPostgres(calculator_connect)
        self.owner_connect=owner_connect;self.worker_connect=worker_connect
        self.repository=PostgresReminders(worker_connect,restricted_worker=True)
        self.catalog=FixtureCatalog(catalog);self.command_key=command_key;self.tick_key=tick_key
        self.tokens=ReviewTokens(review_key);self.transport=transport
        self.development = None
        if development_calendar is not None:
            if transport is not None or not isinstance(development_profile, str) or not re.fullmatch(r"[a-f0-9]{64}", development_profile):
                raise ValueError("Astronomical development mode requires a scoped profile and disabled delivery")
            from dincharya.lunar_development import DevelopmentLunar

            self.development = DevelopmentLunar(self.owner, self.calculator, development_calendar,
                                                development_profile)

    def review(self,request,stage,**context):
        reviewed=self.owner.inspect_request(request)
        token=self.tokens.issue({'request':request,'fingerprint':reviewed['fingerprint'],'stage':stage,**context})
        return token

    def handle(self,value,signature):
        try:
            if (not isinstance(value,dict) or set(value)!={'command','nonce','timestamp'}
                    or type(value['timestamp']) is not int or abs(time.time()-value['timestamp'])>60
                    or not isinstance(value['nonce'],str) or not 1<=len(value['nonce'])<=80):return {'status':'denied'}
            command=value['command']
            if not isinstance(command,dict):return {'status':'denied'}
            op=command['operation']
            key=self.tick_key if op=='tick' else self.command_key
            if not isinstance(signature,str) or not hmac.compare_digest(signature,sign(key,'command',value)):
                return {'status':'denied'}
            if op in DEVELOPMENT_OPERATIONS:
                if self.development is None:
                    return {'status':'disabled','reply':'Lunar scheduling is disabled.'}
                return self.development.handle(command)
            if self.development is not None and op != "tick":
                return {'status':'denied'}
            action=uuid5(NAMESPACE,value['nonce'])
            if op=='request':
                if set(command)!={'operation','kind','fixture'}:raise ValueError()
                kind=command['kind']
                if kind not in ('birthday','wedding_anniversary'):raise ValueError()
                fixture=self.catalog.get(command['fixture'],kind)
                series=uuid5(action,'series')
                request=self.owner.propose_series(action,series,kind,0,fixture['rule'])
                token=self.review(request,'rule',series=str(series),fixture=command['fixture'])
                rule=fixture['rule']
                return {'status':'rule_preview','request':request,'series':str(series),'token':token,
                  'reply':f"SYNTHETIC {kind}: {rule['month']} {rule['paksha']} tithi {rule['tithi']} ({rule['convention']}, {rule['intercalation']}).\n"
                   f"Fixture {fixture['date']} {fixture['time']} Asia/Kolkata. No astronomy prediction.\n"
                   f"Approve the rule: /approve_lunar_rule {token}\nReject: /reject_lunar {token}"}
            if op in ('approve_rule','approve','reject'):
                if set(command)!={'operation','token'}:raise ValueError()
                context=self.tokens.read(command['token']);stage=context['stage']
                if op=='approve_rule' and stage!='rule' or op=='approve' and stage not in ('occurrence','cancel'):raise ValueError()
                result=self.owner.decide(action,context['request'],'reject' if op=='reject' else 'approve',
                                         context['fingerprint'],reviewed=True)
                if op=='reject':return {**result,'reply':'Proposal rejected; no new reminder scheduled.'}
                if result['status']!='approved':return {**result,'reply':'Approval withheld; inspect and review again.'}
                if stage!='rule':return {**result,'reply':'Cancellation approved; history retained.' if stage=='cancel' else 'Reminder scheduled.'}
                series=UUID(context['series']);fixture=self.catalog.get(context['fixture'])
                occurrence=self.calculator.record_calculation(uuid5(series,'calculation'),series,1,fixture['identity'],
                    fixture['rule']['profile'],fixture['evidence'],date.fromisoformat(fixture['date']))
                occurrence=UUID(str(occurrence));snapshot=self.owner.inspect_occurrence(occurrence)
                if snapshot['occurrence']['event_id'] is not None:
                    return {'status':'already_scheduled','occurrence':str(occurrence),'reply':'Already scheduled; inspect status.'}
                request=self.owner.propose_occurrence(uuid5(series,'occurrence-proposal'),occurrence,'select',1,0,
                    snapshot['occurrence']['observation'],{'date':fixture['date'],'title':fixture['title'],'start_time':fixture['time']})
                token=self.review(request,'occurrence')
                return {'status':'occurrence_preview','request':request,'occurrence':str(occurrence),'token':token,
                    'reply':f"Occurrence {occurrence}\nSYNTHETIC {fixture['date']} {fixture['time']} Asia/Kolkata.\n"
                    f"Approve separately: /approve_lunar {token}\nReject: /reject_lunar {token}\nStatus: /lunar_status {occurrence}"}
            if op in ('cancel','status'):
                if set(command)!={'operation','occurrence'}:raise ValueError()
                occurrence=UUID(command['occurrence']);snapshot=self.owner.inspect_occurrence(occurrence)
                if op=='status':
                    with self.owner_connect() as conn:
                        status=conn.execute('SELECT lunar_api.delivery_status(%s)',(occurrence,)).fetchone()[0]
                    return {'status':'inspected','data':status,'reply':canonical(status)}
                row=snapshot['occurrence']
                if row['cancelled']:return {'status':'cancelled','reply':'Already cancelled; history retained.'}
                request=self.owner.propose_occurrence(action,occurrence,'cancel',snapshot['series']['revision'],row['revision'],row['observation'],{})
                token=self.review(request,'cancel')
                return {'status':'cancel_preview','request':request,'token':token,'reply':f'Cancel future work? /approve_lunar {token}'}
            if op=='tick':
                if set(command)!={'operation'}:raise ValueError()
                if self.transport is None:return {'status':'delivery_disabled'}
                with closing(self.worker_connect()) as lease:
                    lease.commit();lease.autocommit=True
                    if not lease.execute('SELECT pg_try_advisory_lock(20261112,3)').fetchone()[0]:return {'status':'busy'}
                    try:return {'status':'processed','completed':process_batch(self.repository,self.transport,lambda:datetime.now(timezone.utc),limit=1)}
                    except DeliveryUncertain:return {'status':'uncertain'}
            raise ValueError()
        except LunarStorageError:return {'status':'unavailable','reply':'Request unavailable or changed; inspect existing status before retrying. No resend was requested.'}
        except Exception:return {'status':'unavailable','reply':'Could not confirm the operation. Inspect status before retrying.'}


def live_transport(post,token,owner_id,*,authorized=False):
    if authorized is not True:raise ValueError('Live Telegram acceptance requires explicit owner authorization')
    return TelegramReminders(post,token,owner_id)
