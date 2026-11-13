"""T00–T26 synthetic lunar acceptance. Imported offline; no connections on import.

Callbacks are supplied exclusively by the pinned disposable PostgreSQL harness.
No Telegram transport, credentials, production paths or database driver here.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier
from uuid import uuid4
import json
import time

ACTORS = ('synthetic_lunar_owner', 'synthetic_lunar_other', 'synthetic_lunar_calculator',
          'synthetic_lunar_worker', 'synthetic_lunar_outsider')
CASES = tuple('T%02d' % n for n in range(27))
PROFILE_SPEC = {'synthetic': True, 'engine_adoption': False}


def literal(value):
    """SQL constants for invented fixture values only; never identifiers/secrets."""
    if value is None:
        return 'NULL'
    if type(value) is bool:
        return 'true' if value else 'false'
    if type(value) is int:
        return str(value)
    if isinstance(value, (dict, list)):
        return "'" + json.dumps(value, sort_keys=True).replace("'", "''") + "'::jsonb"
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    raise ValueError('Unsupported fixture literal')


def call_sql(function, *values):
    allowed = {'propose_series', 'record_calculation', 'propose_occurrence', 'inspect_occurrence',
               'inspect_request', 'inspect_series', 'propose_series_cancel', 'decide'}
    if function not in allowed:
        raise ValueError('Unknown lunar API')
    return 'SELECT lunar_api.' + function + '(' + ','.join(map(literal, values)) + ')'


def run_lunar(query, actor_query, provision_actor, restart_database):
    """Real-role runtime assertions. Never call this without separate execution approval."""
    owner, other, calculator, worker, outsider = ACTORS
    for name in ACTORS:
        query(f'CREATE ROLE {name} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS')
        provision_actor(name)
    query(f'GRANT dincharya_lunar_owner TO {owner},{other}; '
          f'GRANT dincharya_lunar_calculator TO {calculator}; GRANT dincharya_reminder_worker TO {worker}')
    query("INSERT INTO lunar_private.principals(role_oid,role_name,owner_subject,kind,enabled) "
          "SELECT oid,rolname,CASE WHEN rolname='synthetic_lunar_other' THEN 202 ELSE 101 END,"
          "CASE WHEN rolname='synthetic_lunar_calculator' THEN 'calculator' ELSE 'owner' END,true "
          f"FROM pg_roles WHERE rolname IN ('{owner}','{other}','{calculator}')")
    for setting,value in {'log_statement':'none','log_min_error_statement':'panic',
            'log_parameter_max_length':'0','log_parameter_max_length_on_error':'0'}.items():
        assert query('SHOW '+setting)==value, 'Unsafe synthetic server logging'
    PROFILE = query('SELECT lunar_private.hash('+literal(PROFILE_SPEC)+')')
    query("INSERT INTO lunar_private.profiles(digest,specification,enabled) VALUES(" +
          literal(PROFILE) + ",'{\"synthetic\":true,\"engine_adoption\":false}',true)")
    tomorrow = date.fromisoformat(query("SELECT ((clock_timestamp() AT TIME ZONE 'Asia/Kolkata')::date+2)::text").splitlines()[-1])
    passed = []

    def done(case):
        assert case not in passed
        passed.append(case)
        print('PASS lunar ' + case, flush=True)

    def api(name, *values, actor=owner, error=None):
        result = actor_query(actor, call_sql(name, *values), error)
        if error:
            return result
        line = result.splitlines()[-1]
        return json.loads(line) if line.startswith(('{', '[')) else line

    def rule(**overrides):
        return dict(convention='purnimanta', month='chaitra', intercalation='both', paksha='shukla',
                    tithi=5, repeated='review', birth_basis='explicit_rule', profile=PROFILE, **overrides)

    def decision(request, *, decision='approve', force=False, action=None, fingerprint=None, actor=owner, error=None):
        review = api('inspect_request', int(request), actor=actor) if fingerprint is None else None
        return api('decide', action or str(uuid4()), int(request), decision,
                   fingerprint or review['fingerprint'], True, force, actor=actor, error=error)

    def series(*, purpose='birthday', own=owner, custom=None):
        sid = str(uuid4())
        request = api('propose_series', str(uuid4()), sid, purpose, 0, custom or rule(), actor=own)
        assert decision(request, actor=own)['status'] == 'approved'
        return sid

    def calc(sid, *, cycle=330, day=None, adhika=False, action=None, evidence=None, revision=1, profile=PROFILE):
        day = day or tomorrow.isoformat()
        identity = dict(version=2, convention='purnimanta', month='chaitra', intercalation='adhika' if adhika else 'ordinary',
                        lunation_cycle=cycle, paksha='shukla', tithi=5)
        ev = dict(status='selected', month_status='supported', date_gate='pass', kshaya=False,
                  ambiguous=False, skipped=False, repeated=False, selection=day,
                  birth_basis='explicit_rule', repetition_policy='review',
                  interval_start=day+'T00:00:00+05:30', interval_end=day+'T23:59:59+05:30')
        if evidence:
            ev.update(evidence)
        return api('record_calculation', action or str(uuid4()), sid, revision, identity, profile, ev, day, actor=calculator)

    def proposal(occ, *, operation='select', day=None, start='12:00', action=None):
        snap = api('inspect_occurrence', occ)
        desired = {} if operation=='cancel' else dict(date=day or tomorrow.isoformat(), title='Synthetic lunar event', start_time=start)
        return api('propose_occurrence', action or str(uuid4()), occ, operation,
                   snap['series']['revision'], snap['occurrence']['revision'], snap['occurrence']['observation'], desired)

    def projected(*, cycle=330, start='12:00'):
        sid = series()
        occ = calc(sid, cycle=cycle)
        req = proposal(occ, start=start)
        result = decision(req, force=True)
        assert result['status'] == 'approved'
        return sid, occ, int(result['event_id'])

    def rows(event):
        return query(f"SELECT coalesce(jsonb_agg(to_jsonb(d) ORDER BY id),'[]') FROM public.reminder_deliveries d WHERE event_id={event}")

    def seed(event, state='pending', attempts=0, *, expired=False):
        # Administrator-only invented previously-approved history. One server clock.
        # No API or production caller has this fixture path.
        query("BEGIN; SET LOCAL ROLE dincharya_lunar_executor; "
              f"UPDATE public.schedule_events SET event_date=((now()-interval '2 minutes') AT TIME ZONE 'Asia/Kolkata')::date,"
              f"start_time=((now()-interval '2 minutes') AT TIME ZONE 'Asia/Kolkata')::time WHERE id={event}; "
              f"UPDATE public.recurrence_rules SET start_date=((now()-interval '2 minutes') AT TIME ZONE 'Asia/Kolkata')::date WHERE event_id={event}; COMMIT;")
        token = "gen_random_uuid()" if state=='sending' else 'NULL'
        lease = "now()-interval '1 second'" if expired else "now()+interval '2 minutes'"
        query("INSERT INTO public.reminder_deliveries(event_id,occurrence_date,status,managed_by,due_at,payload,attempts,retry_at,"
              "worker_token,lease_until,claimed_at) VALUES(" + str(event) +
              ",((now()-interval '2 minutes') AT TIME ZONE 'Asia/Kolkata')::date," + literal(state) +
              f",'m2e',now()-interval '2 minutes','{{}}',{attempts},now()-interval '2 minutes',"
              f"{token},{lease if state=='sending' else 'NULL'},now()-interval '1 minute') RETURNING id")
        return int(query(f'SELECT max(id) FROM public.reminder_deliveries WHERE event_id={event}'))

    def parallel(*operations):
        barrier = Barrier(len(operations))
        def invoke(fn):
            barrier.wait(timeout=10)
            return fn()
        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            return [future.result(timeout=100) for future in [pool.submit(invoke, op) for op in operations]]

    # T00: default-denied catalogs and environment; existing harness checks image,
    # migration checksums/legacy functions and invariance of original containers.
    assert query("SELECT count(*) FROM pg_auth_members WHERE roleid='dincharya_lunar_executor'::regrole") == '0'
    assert query("SELECT count(*) FROM pg_roles WHERE rolname LIKE 'dincharya_lunar_%' AND (rolsuper OR rolcanlogin OR rolbypassrls)") == '0'
    assert query("SHOW password_encryption") == 'scram-sha-256'
    assert query("SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL OR "
                 "(type LIKE 'host%' AND auth_method<>'scram-sha-256') OR "
                 "(auth_method='trust' AND type<>'local')")=='0'
    assert query("SELECT enabled FROM reconcile_private.gate")=='f'
    actor_query(owner, 'SELECT 1', 'AUTH')
    done('T00')

    # T01
    sid = series()
    actor_query(worker, call_sql('propose_series',str(uuid4()),str(uuid4()),'birthday',0,rule()),'42501')
    actor_query(outsider, call_sql('inspect_request',1),'42501')
    actor_query(owner,'SET ROLE dincharya_lunar_executor','42501')
    query(f"UPDATE lunar_private.principals SET enabled=false WHERE role_name='{owner}'")
    api('propose_series',str(uuid4()),str(uuid4()),'birthday',0,rule(),error='42501')
    query(f"UPDATE lunar_private.principals SET enabled=true WHERE role_name='{owner}'")
    done('T01')

    # T02
    bad = rule(); bad['actor_id']=101
    api('propose_series',str(uuid4()),str(uuid4()),'birthday',0,bad,error='22023')
    malformed=rule(); malformed['month']="chaitra'); DROP SCHEMA lunar_private CASCADE; --"
    api('propose_series',str(uuid4()),str(uuid4()),'birthday',0,malformed,error='22023')
    done('T02')

    # T03
    sid2=str(uuid4()); rq=api('propose_series',str(uuid4()),sid2,'wedding_anniversary',0,rule())
    assert query(f"SELECT count(*) FROM lunar_private.occurrences WHERE series_id='{sid2}'")=='0'
    assert decision(rq,decision='reject')['status']=='rejected'
    assert query(f"SELECT revision FROM lunar_private.series WHERE id='{sid2}'")=='0'
    done('T03')

    # T04: two distinct overlapping calculation submissions, identical semantics.
    occurrences=parallel(lambda:calc(sid), lambda:calc(sid))
    assert occurrences[0]==occurrences[1]; occ=occurrences[0]
    assert api('inspect_occurrence',occ)['occurrence']['observation']==1
    for bad_date,bad_time in [(tomorrow.isoformat(),'now'),('tomorrow','12:00'),(tomorrow.strftime('%d/%m/%Y'),'12:00')]:
        api('propose_occurrence',str(uuid4()),occ,'select',1,0,1,
            dict(date=bad_date,title='Synthetic relative time rejection',start_time=bad_time),error='22023')
    action=str(uuid4()); rq=proposal(occ,action=action)
    assert proposal(occ,action=action)==rq
    assert query(f"SELECT count(*) FROM public.schedule_events e JOIN lunar_private.occurrences o ON o.event_id=e.id WHERE o.id='{occ}'")=='0'
    done('T04')

    # T05
    assert decision(rq,force=True)['status']=='approved'
    wedding=series(purpose='wedding_anniversary'); wo=calc(wedding); wr=proposal(wo)
    blocked=decision(wr)
    assert blocked['status']=='conflict'
    assert decision(wr,force=True)['status']=='approved'
    assert api('inspect_occurrence',wo)['occurrence']['event_id']!=api('inspect_occurrence',occ)['occurrence']['event_id']
    done('T05')

    # T06
    sibling=calc(sid,adhika=True); assert api('inspect_occurrence',sibling)['occurrence']['event_id'] is None
    done('T06')

    # T07: same-action replay and competing approve/reject decisions.
    sid3=series(); o3=calc(sid3); r3=proposal(o3); fp=api('inspect_request',int(r3))['fingerprint']; act=str(uuid4())
    outcomes=parallel(lambda:decision(r3,action=act,fingerprint=fp,force=True),lambda:decision(r3,action=act,fingerprint=fp,force=True))
    assert outcomes[0]==outcomes[1]
    decision(r3,decision='reject',fingerprint=fp,error='22023')
    # Capture only expected stale SQLSTATE, not arbitrary runner failures.
    race_series=series();race_occ=calc(race_series);race_req=proposal(race_occ)
    race_fp=api('inspect_request',int(race_req))['fingerprint']
    def competing(kind):
        statement=call_sql('decide',str(uuid4()),int(race_req),kind,race_fp,True,True)
        # A fixture-only anonymous block records expected stale outcome in NOTICE;
        # the durable request/audit counts below establish the winner.
        return actor_query(owner,"DO $test$ BEGIN PERFORM x FROM ("+statement+
          ") v(x); EXCEPTION WHEN SQLSTATE '22023' THEN NULL; END $test$;")
    parallel(lambda:competing('approve'),lambda:competing('reject'))
    assert query(f"SELECT count(*) FROM lunar_private.actions WHERE request_id={race_req} AND result->>'status' IN ('approved','rejected')")=='1'
    done('T07')

    # T08
    sid4=series(); o4=calc(sid4); r4=proposal(o4); fp4=api('inspect_request',int(r4))['fingerprint']
    calc(sid4,day=(tomorrow+timedelta(days=1)).isoformat());calc(sid4)
    decision(r4,fingerprint=fp4,error='22023')
    done('T08')

    # T09: same-date changed birth policy requires approved rule + new observation.
    changed=rule();changed['birth_basis']='sunrise'
    rr=api('propose_series',str(uuid4()),sid4,'birthday',1,changed)
    assert query(f"SELECT revision FROM lunar_private.series WHERE id='{sid4}'")=='1'
    assert decision(rr)['status']=='approved'
    api('propose_occurrence',str(uuid4()),o4,'select',1,0,3,dict(date=tomorrow.isoformat(),title='Synthetic',start_time='12:00'),error='22023')
    calc(sid4,revision=2,evidence={'birth_basis':'sunrise'})
    assert api('inspect_occurrence',o4)['occurrence']['event_id'] is None
    done('T09')

    repetition=rule();repetition['birth_basis']='sunrise';repetition['repeated']='last'
    policy_req=api('propose_series',str(uuid4()),sid4,'birthday',2,repetition)
    assert decision(policy_req)['status']=='approved'
    assert api('inspect_occurrence',o4)['occurrence']['event_id'] is None

    # T10: audit failure must roll back native event, child request and approval.
    sid5=series();o5=calc(sid5);r5=proposal(o5); before=query('SELECT count(*) FROM public.schedule_events')
    query("CREATE FUNCTION public.synthetic_lunar_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic audit fault' USING ERRCODE='P0001'; END $$; "
          "CREATE TRIGGER synthetic_lunar_fail BEFORE INSERT ON lunar_private.actions FOR EACH ROW EXECUTE FUNCTION public.synthetic_lunar_fail()")
    decision(r5,force=True,error='P0001')
    assert query('SELECT count(*) FROM public.schedule_events')==before
    assert query(f"SELECT revision=0 AND event_id IS NULL FROM lunar_private.occurrences WHERE id='{o5}'")=='t'
    assert query(f'SELECT status FROM public.schedule_change_requests WHERE id={r5}')=='pending'
    query('DROP TRIGGER synthetic_lunar_fail ON lunar_private.actions; DROP FUNCTION public.synthetic_lunar_fail()')
    done('T10')

    # T11
    act=str(uuid4());fp=api('inspect_request',int(r5))['fingerprint']; saved=decision(r5,action=act,fingerprint=fp,force=True)
    assert decision(r5,action=act,fingerprint=fp,force=True)==saved
    decision(r5,action=act,fingerprint=fp,force=False,error='22023')
    api('inspect_request',int(r5),actor=other,error='22023')
    stable_review=api('inspect_request',int(r5))
    alternate=actor_query(owner,"SET TimeZone='Pacific/Honolulu'; SET DateStyle='SQL,DMY'; "+call_sql('inspect_request',int(r5)))
    assert json.loads(alternate.splitlines()[-1])==stable_review
    query(f"UPDATE lunar_private.principals SET enabled=false WHERE role_name='{owner}'")
    decision(r5,action=act,fingerprint=fp,force=True,error='42501')
    query(f"UPDATE lunar_private.principals SET enabled=true,owner_subject=202 WHERE role_name='{owner}'")
    decision(r5,action=act,fingerprint=fp,force=True,error='22023')
    query(f"UPDATE lunar_private.principals SET owner_subject=101 WHERE role_name='{owner}'")
    done('T11')

    # T12
    sid6,o6,e6=projected(); new_day=(tomorrow+timedelta(days=1)).isoformat()
    query(f"INSERT INTO public.reminder_deliveries(event_id,occurrence_date,status,managed_by,attempts) VALUES({e6},'{tomorrow}','pending','m2e',0)")
    calc(sid6,day=new_day); replacement=proposal(o6,operation='replace',day=new_day)
    assert decision(replacement,force=True)['event_id']==e6
    assert query(f"SELECT e.event_date=r.start_date FROM public.schedule_events e JOIN public.recurrence_rules r ON r.event_id=e.id WHERE e.id={e6}")=='t'
    assert query(f"SELECT status FROM public.reminder_deliveries WHERE event_id={e6}")=='cancelled'
    done('T12')

    # T13
    for state,attempts in [('sent',1),('uncertain',1),('failed',1),('dead',5)]:
        si,oi,ei=projected();seed(ei,state,attempts); history=rows(ei)
        calc(si,day=new_day); replacement=proposal(oi,operation='replace',day=new_day)
        decision(replacement,force=True,error='55000');assert rows(ei)==history
    done('T13')

    # T14
    si,oi,ei=projected(); seed(ei);cancel=proposal(oi,operation='cancel')
    assert decision(cancel)['status']=='approved'
    query('SELECT public.refresh_occurrence_reminders()');query('SELECT public.refresh_occurrence_reminders()')
    assert query(f"SELECT enabled FROM public.schedule_events WHERE id={ei}")=='f'
    assert query(f"SELECT status FROM public.reminder_deliveries WHERE event_id={ei}")=='cancelled'
    snap=api('inspect_occurrence',oi)
    api('propose_occurrence',str(uuid4()),oi,'select',1,snap['occurrence']['revision'],snap['occurrence']['observation'],{},error='22023')
    done('T14')

    # T15: exact bounded cancellation manifest; a leased member blocks ALL.
    si,oi,ei=projected();delivery=seed(ei,'sending',1)
    manifest=api('inspect_series',si)['manifest']; sc=api('propose_series_cancel',str(uuid4()),si,1,manifest)
    decision(sc,error='55000')
    assert query(f"SELECT enabled FROM lunar_private.series WHERE id='{si}'")=='t'
    query(f"UPDATE public.reminder_deliveries SET status='uncertain',worker_token=NULL,lease_until=NULL WHERE id={delivery}")
    assert decision(sc)['status']=='approved'
    assert query(f"SELECT enabled FROM lunar_private.series WHERE id='{si}'")=='f'
    # New occurrence approval versus exact cancel manifest: one wins; the
    # other must reject its stale review, never partially cancel a series.
    si_r,oi_r,ei_r=projected();o_new=calc(si_r,cycle=331,day=new_day)
    r_new=proposal(o_new,day=new_day)
    cancel_r=api('propose_series_cancel',str(uuid4()),si_r,1,api('inspect_series',si_r)['manifest'])
    fp_new=api('inspect_request',int(r_new))['fingerprint'];fp_cancel=api('inspect_request',int(cancel_r))['fingerprint']
    def racing_request(req_id,fingerprint):
        statement=call_sql('decide',str(uuid4()),int(req_id),'approve',fingerprint,True,True)
        return actor_query(owner,"DO $test$ BEGIN PERFORM x FROM ("+statement+
          ") v(x); EXCEPTION WHEN SQLSTATE '22023' THEN NULL; END $test$;")
    parallel(lambda:racing_request(r_new,fp_new),lambda:racing_request(cancel_r,fp_cancel))
    enabled=query(f"SELECT enabled FROM lunar_private.series WHERE id='{si_r}'")
    if enabled=='f':
        assert query(f"SELECT count(*) FROM public.schedule_events e JOIN lunar_private.occurrences x ON x.event_id=e.id WHERE x.series_id='{si_r}' AND e.enabled")=='0'
    else:
        assert query(f"SELECT count(*) FROM lunar_private.occurrences WHERE series_id='{si_r}' AND event_id IS NOT NULL AND NOT cancelled")=='2'
    done('T15')

    # T16: give the hostile ordinary role raw rights ONLY for testing trigger barrier.
    query(f'GRANT SELECT,UPDATE ON public.schedule_events,public.recurrence_rules TO {owner}')
    query(f'GRANT SELECT ON public.schedule_change_requests TO {owner}')
    actor_query(owner,f'UPDATE public.schedule_events SET enabled=true WHERE id={ei}','42501')
    actor_query(owner,f"UPDATE public.recurrence_rules SET start_date='{new_day}' WHERE event_id={ei}",'42501')
    query(f'REVOKE UPDATE ON public.schedule_events,public.recurrence_rules FROM {owner}')
    assert actor_query(owner,f"SELECT success FROM public.dispatch_schedule_decision({sc},101,'approve',true)")=='f'
    query(f'GRANT INSERT,UPDATE ON public.schedule_change_requests,public.schedule_occurrence_overrides TO {owner}')
    query(f'GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {owner}')
    actor_query(owner,f"INSERT INTO public.schedule_change_requests(action,event_id,requested_by,proposed_data) "
                f"VALUES('update',{ei},101,'{{\"api_version\":2}}')",'42501')
    actor_query(owner,f"INSERT INTO public.schedule_occurrence_overrides(event_id,occurrence_date,cancelled) "
                f"VALUES({ei},'{tomorrow}',true)",'42501')
    # Seed a pre-existing pending native decision under administrator authority;
    # the caller-ID API must still fail at mutation time after lunar mapping.
    native_desired=dict(title='Synthetic pending native request',start_time='15:00',timezone='Asia/Kolkata',
       recurrence_rule=dict(calendar_system='gregorian',frequency='once',interval_count=1,start_date=new_day))
    pending_output=query("BEGIN; SET LOCAL ROLE dincharya_lunar_executor; SELECT public.propose_gregorian_change("
       "'update','series',"+str(e6)+",NULL,"+literal(native_desired)+",101); COMMIT;")
    pending=next(line for line in pending_output.splitlines() if line.isdigit())
    query(f'GRANT UPDATE ON public.schedule_events,public.recurrence_rules TO {owner}')
    actor_query(owner,f"SELECT * FROM public.decide_gregorian_change({pending},101,'approve',true)",'42501')
    assert query(f'SELECT status FROM public.schedule_change_requests WHERE id={pending}')=='pending'
    assert actor_query(owner,f"SELECT success FROM public.process_schedule_decision({pending},101,'approve',true)")=='f'
    query(f'REVOKE UPDATE ON public.schedule_events,public.recurrence_rules FROM {owner}')
    query(f'REVOKE INSERT,UPDATE ON public.schedule_change_requests,public.schedule_occurrence_overrides FROM {owner}')
    query(f'REVOKE SELECT ON public.schedule_change_requests FROM {owner}')
    query(f'REVOKE USAGE ON ALL SEQUENCES IN SCHEMA public FROM {owner}')
    done('T16')

    # T17: genuine API-approved projection -> refresh -> due claim -> synthetic
    # receipt acknowledgement. No administrator date rewrite or artificial p_now.
    due=json.loads(query("SELECT jsonb_build_object('day',(d AT TIME ZONE 'Asia/Kolkata')::date,"
        "'time',(d AT TIME ZONE 'Asia/Kolkata')::time,'instant',d) FROM "
        "(SELECT clock_timestamp()+interval '30 seconds' d) v"))
    si=series();oi=calc(si,day=due['day']);rr=proposal(oi,day=due['day'],start=due['time'])
    approved=decision(rr,force=True);assert approved['status']=='approved';ei=int(approved['event_id'])
    query('SELECT public.refresh_occurrence_reminders()')
    di=int(query(f'SELECT id FROM public.reminder_deliveries WHERE event_id={ei}'))
    deadline=time.monotonic()+45
    while query('SELECT clock_timestamp()>='+literal(due['instant'])+'::timestamptz')!='t':
        assert time.monotonic()<deadline,'Synthetic due-time wait exceeded bound'
        time.sleep(.1)
    claim="SELECT coalesce(jsonb_agg(to_jsonb(x)),'[]') FROM reminder_worker_api.claim_occurrence_reminders(now(),100) x"
    claims=parallel(lambda:json.loads(actor_query(worker,claim)),lambda:json.loads(actor_query(worker,claim)))
    matching=[r for batch in claims for r in batch if r['delivery_id']==di]
    assert len(matching)==1; token=matching[0]['worker_token']
    assert actor_query(worker,f"SELECT reminder_worker_api.acknowledge_occurrence_reminder({di},'{token}','sent',now(),801,802)")=='t'
    assert query(f"SELECT status='sent' AND telegram_chat_id=801 AND telegram_message_id=802 FROM public.reminder_deliveries WHERE id={di}")=='t'
    done('T17')

    # T18: claim-first rejects; cancellation-first is never claimed.
    si,oi,ei=projected();di=seed(ei,'sending',1)
    token=query(f'SELECT worker_token FROM public.reminder_deliveries WHERE id={di}')
    req=proposal(oi,operation='cancel');decision(req,error='55000')
    si2,oi2,ei2=projected();di2=seed(ei2);assert decision(proposal(oi2,operation='cancel'))['status']=='approved'
    assert all(r['delivery_id']!=di2 for r in json.loads(actor_query(worker,claim)))
    # Hold the same scheduler mutex across a real decision and a worker wait.
    si_r,oi_r,ei_r=projected();di_r=seed(ei_r);rr=proposal(oi_r,operation='cancel')
    review_r=api('inspect_request',int(rr));action_r=str(uuid4())
    statement_r=call_sql('decide',action_r,int(rr),'approve',review_r['fingerprint'],True,False)
    def await_wait(name,kind):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            if query("SELECT count(*) FROM pg_stat_activity WHERE application_name="+literal(name)+
                     ' AND wait_event_type='+literal(kind))=='1':return
            time.sleep(.02)
        raise AssertionError('Expected isolated lock ordering was not observed')
    with ThreadPoolExecutor(max_workers=2) as pool:
        holder=pool.submit(actor_query,owner,"SET application_name='synthetic_lunar_cancel_holder'; BEGIN; "
            "SELECT pg_advisory_xact_lock(20261112,1); SELECT pg_sleep(2); "+statement_r+'; COMMIT;')
        await_wait('synthetic_lunar_cancel_holder','Timeout')
        claimant=pool.submit(actor_query,worker,"SET application_name='synthetic_lunar_claim_waiter'; "+claim)
        await_wait('synthetic_lunar_claim_waiter','Lock')
        holder.result(timeout=15)
        claim_result=json.loads(claimant.result(timeout=15).splitlines()[-1])
        assert all(r['delivery_id']!=di_r for r in claim_result)
    # Claim-first holds uncommitted send state; a reviewed decision waits and
    # then rejects its now-stale fingerprint after the worker commits.
    si_r,oi_r,ei_r=projected();di_r=seed(ei_r);rr=proposal(oi_r,operation='cancel')
    review_r=api('inspect_request',int(rr));statement_r=call_sql('decide',str(uuid4()),int(rr),'approve',review_r['fingerprint'],True,False)
    with ThreadPoolExecutor(max_workers=2) as pool:
        holder=pool.submit(actor_query,worker,"SET application_name='synthetic_lunar_claim_holder'; BEGIN; "+
            claim+"; SELECT pg_sleep(2); COMMIT;")
        await_wait('synthetic_lunar_claim_holder','Timeout')
        decider=pool.submit(actor_query,owner,"SET application_name='synthetic_lunar_decide_waiter'; "+statement_r,'22023')
        await_wait('synthetic_lunar_decide_waiter','Lock')
        holder.result(timeout=15);decider.result(timeout=15)
    done('T18')

    # T19
    query(f"UPDATE public.reminder_deliveries SET lease_until=now()-interval '1 second' WHERE id={di}")
    decision(req,error='55000')
    query('SELECT public.refresh_occurrence_reminders()')
    assert actor_query(worker,f"SELECT reminder_worker_api.finish_occurrence_reminder({di},'{token}','sent',now())")=='f'
    assert query(f'SELECT status FROM public.reminder_deliveries WHERE id={di}')=='uncertain'
    done('T19')

    # T20
    si,oi,ei=projected();di=seed(ei,'sending',5)
    tk=query(f'SELECT worker_token FROM public.reminder_deliveries WHERE id={di}')
    assert actor_query(worker,f"SELECT reminder_worker_api.finish_occurrence_reminder({di},'{tk}','not_accepted',now())")=='t'
    assert query(f'SELECT status FROM public.reminder_deliveries WHERE id={di}')=='dead'
    si,oi,ei=projected();di=seed(ei,'sending',1);tk=query(f'SELECT worker_token FROM public.reminder_deliveries WHERE id={di}')
    actor_query(worker,f"SELECT reminder_worker_api.finish_occurrence_reminder({di},'{tk}','not_accepted',now())")
    assert query(f"SELECT status='failed' AND retry_at>=now()+interval '25 seconds' FROM public.reminder_deliveries WHERE id={di}")=='t'
    done('T20')

    # T21
    receipts=[]
    for _ in range(2):
        si,oi,ei=projected();di=seed(ei,'sending',1);tk=query(f'SELECT worker_token FROM public.reminder_deliveries WHERE id={di}')
        receipts.append((ei,di,tk))
    ei,di,tk=receipts[0]
    assert actor_query(worker,f"SELECT reminder_worker_api.acknowledge_occurrence_reminder({di},'{tk}','sent',now(),901,902)")=='t'
    ei,di,tk=receipts[1];before=rows(ei)
    actor_query(worker,f"SELECT reminder_worker_api.acknowledge_occurrence_reminder({di},'{tk}','sent',now(),901,902)",'23505')
    assert rows(ei)==before
    done('T21')

    # T22: unmapped native decision still functions and snapshots unchanged by guard.
    desired=dict(title='Synthetic Gregorian control',start_time='03:00',timezone='Asia/Kolkata',
                 recurrence_rule=dict(calendar_system='gregorian',frequency='once',interval_count=1,start_date=new_day))
    native=query("SELECT public.propose_gregorian_change('add','series',NULL,NULL,"+literal(desired)+',101)')
    assert query(f"SELECT success FROM public.decide_gregorian_change({native},101,'approve',true)")=='t'
    native_event=query(f'SELECT event_id FROM public.schedule_change_requests WHERE id={native}')
    query(f"INSERT INTO public.schedule_occurrence_overrides(event_id,occurrence_date,cancelled) VALUES({native_event},'{new_day}',true)")
    assert query(f"SELECT count(*) FROM public.generate_event_occurrences('{new_day}','{new_day}') WHERE event_id={native_event}")=='0'
    remove=query(f"SELECT public.propose_gregorian_change('remove','series',{native_event},NULL,'{{}}',101)")
    assert query(f"SELECT success FROM public.decide_gregorian_change({remove},101,'approve')")=='t'
    done('T22')

    # T23
    si=series()
    for bad in ({'kshaya':True},{'ambiguous':True},{'skipped':True},{'status':'review'},
                {'month_status':'unsupported'},{'date_gate':'review'},{'repeated':True}):
        identity=dict(version=2,convention='purnimanta',month='chaitra',intercalation='ordinary',lunation_cycle=330,paksha='shukla',tithi=5)
        ev=dict(status='selected',month_status='supported',date_gate='pass',kshaya=False,ambiguous=False,skipped=False,
                repeated=False,selection=tomorrow.isoformat(),birth_basis='explicit_rule',repetition_policy='review',
                interval_start=str(tomorrow)+'T00:00:00+05:30',interval_end=str(tomorrow)+'T23:59:59+05:30');ev.update(bad)
        api('record_calculation',str(uuid4()),si,1,identity,PROFILE,ev,tomorrow.isoformat(),actor=calculator,error='22023')
    unresolved=api('record_calculation',str(uuid4()),si,1,identity,PROFILE,{'status':'review','kshaya':True},None,actor=calculator)
    snap=api('inspect_occurrence',unresolved)
    api('propose_occurrence',str(uuid4()),unresolved,'select',1,0,snap['occurrence']['observation'],
        {'date':tomorrow.isoformat(),'title':'Synthetic','start_time':'12:00'},error='22023')
    assert snap['occurrence']['event_id'] is None
    done('T23')

    # T24: same-key unchanged date recalculation never creates a new projection.
    si,oi,ei=projected();before=rows(ei);calc(si)
    assert api('inspect_occurrence',oi)['occurrence']['event_id']==ei and rows(ei)==before
    assert decision(proposal(oi,operation='replace'),force=True)['event_id']==ei
    new_profile=query("SELECT lunar_private.hash('{\"synthetic_profile\":2}')")
    query("INSERT INTO lunar_private.profiles(digest,specification,enabled) VALUES("+
          literal(new_profile)+",'{\"synthetic_profile\":2}',true)")
    profile_rule=rule();profile_rule['profile']=new_profile
    change_req=api('propose_series',str(uuid4()),si,'birthday',1,profile_rule)
    assert decision(change_req)['status']=='approved'
    calc(si,revision=2,profile=new_profile)
    assert decision(proposal(oi,operation='replace'),force=True)['event_id']==ei
    assert rows(ei)==before
    changed=rule();changed['month']='vaishakha';changed['profile']=new_profile
    identity_req=api('propose_series',str(uuid4()),si,'birthday',2,changed)
    decision(identity_req,error='55000')
    done('T24')

    # T25
    for table in ('actions','calculations','profiles'):
        actor_query(owner,f'DELETE FROM lunar_private.{table}','42501')
        actor_query(worker,f'TRUNCATE lunar_private.{table}','42501')
        query("DO $$ BEGIN BEGIN DELETE FROM lunar_private."+table+"; EXCEPTION WHEN SQLSTATE '55000' THEN RETURN; END; "
              "RAISE EXCEPTION 'missing immutable row protection'; END $$")
    done('T25')

    # T26: crash/restart ONLY the disposable postmaster, preserving tmpfs/container.
    terminal_before=query("SELECT coalesce(jsonb_agg(to_jsonb(d) ORDER BY id),'[]') FROM public.reminder_deliveries d WHERE status IN ('sent','uncertain','dead')")
    restart_database()
    assert query("SELECT coalesce(jsonb_agg(to_jsonb(d) ORDER BY id),'[]') FROM public.reminder_deliveries d WHERE status IN ('sent','uncertain','dead')")==terminal_before
    assert decision(r5,action=act,fingerprint=fp,force=True)==saved
    assert query("SELECT count(*) FROM (SELECT series_id,convention,month,intercalation,lunation_cycle,paksha,tithi "
                 "FROM lunar_private.occurrences GROUP BY 1,2,3,4,5,6,7 HAVING count(*)>1) x")=='0'
    assert query("SELECT count(*) FROM lunar_private.actions a JOIN public.schedule_change_requests q ON q.id=a.request_id "
                 "WHERE a.result->>'status'='approved' AND q.status<>'approved'")=='0'
    done('T26')
    assert passed==list(CASES)
