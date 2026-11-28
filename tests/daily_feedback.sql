-- Invented fixture only. This input must never be applied to a retained ledger.
DO $$ BEGIN
 IF current_database()<>'dincharya_personal_candidate' OR EXISTS(SELECT FROM beta.authority)
 THEN RAISE EXCEPTION 'fresh fixture required'; END IF;
END $$;
INSERT INTO beta.authority(singleton,recipient,bot,enabled,lookback)
 VALUES(true,901,902,true,interval '5 minutes');
INSERT INTO beta.proposal(request_id,epoch,expires,title,frequency,starts,at_time,offsets,state)
 SELECT n,epoch,now()+interval '1 hour','Fixture rule','once',current_date+2,make_time(10,n%60,n/60),'{}','active'
 FROM beta.authority CROSS JOIN generate_series(1,105) n;
INSERT INTO beta.lunar_reference
 SELECT 'fixture-amanta-krishna-10','ordinary',extract(year FROM d),d,'single'
 FROM (VALUES(current_date+1), (make_date(extract(year FROM current_date+1)::int+1,1,1))) v(d);
INSERT INTO beta.live_release(epoch,digest,profile,opens,closes,started)
 SELECT epoch,repeat('a',64),'daily',now()-interval '1 minute',now()+interval '1 hour',true FROM beta.authority;
SET SESSION AUTHORIZATION personal_gateway;
SELECT beta.acquire();
DO $$
BEGIN
 IF NOT beta.reserve_model(901,902,repeat('a',64),3,100,50)
 OR NOT beta.reserve_model(901,902,repeat('a',64),3,100,50)
 THEN RAISE EXCEPTION 'budget did not reserve'; END IF;
 IF beta.reserve_model(901,902,repeat('a',64),3,100,50)
 OR beta.reserve_model(901,902,repeat('a',64),5,1000,50)
 OR beta.reserve_model(901,902,repeat('b',64),5,1000,50)
 THEN RAISE EXCEPTION 'budget exceeded or invalid release'; END IF;
END $$;
DO $$
DECLARE a date:=current_date+1; p uuid; t uuid; decision record;
BEGIN
 IF (SELECT count(*) FROM beta.ui_rules(901,902))<>100 THEN RAISE EXCEPTION 'rule page limit'; END IF;
 BEGIN
   PERFORM * FROM beta.ui_draft_lunar(999,902,201,'Foreign',a,'11:00','{0}',
      'fixture-amanta-krishna-10','ordinary',true,'instant','review');
   RAISE EXCEPTION 'owner fence missing';
 EXCEPTION WHEN no_data_found THEN NULL;
 END;
 BEGIN
   PERFORM * FROM beta.ui_draft_lunar(901,902,201,'Unsupported',a,'11:00','{0}',
      'fixture-amanta-krishna-10','adhika',true,'instant','review');
   RAISE EXCEPTION 'unsupported date was accepted' USING ERRCODE='P9001';
 EXCEPTION WHEN SQLSTATE 'P0001' THEN NULL;
 END;
 SELECT proposal,ticket INTO STRICT p,t FROM beta.ui_draft_lunar(901,902,201,'Lunar fixture',a,'11:00','{0,30}',
      'fixture-amanta-krishna-10','ordinary',true,'instant','review');
 IF EXISTS(SELECT FROM beta.ui_upcoming(901,902,a,a)) THEN RAISE EXCEPTION 'unapproved occurrence'; END IF;
 IF NOT beta.ui_finish(901,902,t,true,201) THEN RAISE EXCEPTION 'preview receipt'; END IF;
 SELECT * INTO decision FROM beta.ui_decide(901,902,p,202,true);
 IF FOUND THEN RAISE EXCEPTION 'wrong message origin'; END IF;
 SELECT * INTO STRICT decision FROM beta.ui_decide(901,902,p,201,true);
 IF decision.status<>'active' THEN RAISE EXCEPTION 'confirmation failed'; END IF;
 SELECT * INTO STRICT decision FROM beta.ui_decide(901,902,p,201,true);
 IF decision.status<>'active' THEN RAISE EXCEPTION 'replay not idempotent'; END IF;
 IF (SELECT count(*) FROM beta.ui_upcoming(901,902,a,a))<>1 THEN RAISE EXCEPTION 'materialization'; END IF;
 IF NOT beta.ui_is_lunar(901,902,p) THEN RAISE EXCEPTION 'lunar projection identity'; END IF;
 BEGIN
   PERFORM * FROM beta.ui_change_draft(901,902,202,p,'replace','Civil replacement','once',a,'13:00','{}');
   RAISE EXCEPTION 'lunar replacement not fenced' USING ERRCODE='P9002';
 EXCEPTION WHEN SQLSTATE 'P0001' THEN NULL;
 END;
 BEGIN
   PERFORM * FROM beta.lunar_schedule;
   RAISE EXCEPTION 'direct gateway access';
 EXCEPTION WHEN insufficient_privilege THEN NULL;
 END;
END $$;
SELECT pg_advisory_unlock(943821,1);
RESET SESSION AUTHORIZATION;
SET SESSION AUTHORIZATION personal_worker;
SELECT beta.acquire();
SELECT beta.roll_forward();
SELECT beta.roll_forward();
SELECT pg_advisory_unlock(943821,2);
RESET SESSION AUTHORIZATION;
DO $$
DECLARE p uuid:=(SELECT id FROM beta.proposal WHERE request_id=201);
BEGIN
 IF (SELECT count(*) FROM beta.occurrence WHERE rule=p)<>2 THEN RAISE EXCEPTION 'annual projection'; END IF;
 IF (SELECT count(*) FROM beta.slot s JOIN beta.occurrence o ON o.id=s.occurrence WHERE o.rule=p)<>4
 THEN RAISE EXCEPTION 'annual slot count'; END IF;
END $$;
SET SESSION AUTHORIZATION personal_gateway;
SELECT beta.acquire();
DO $$
DECLARE a date:=current_date+1; p uuid; c uuid; t uuid; outcome text;
BEGIN
 SELECT id INTO STRICT p FROM beta.ui_rules(901,902) WHERE title='Lunar fixture';
 -- The older civil page is limited to 100; only the established token is used for cancellation.
 SELECT proposal,ticket INTO STRICT c,t FROM beta.ui_change_draft(901,902,210,p,'cancel',NULL,NULL,NULL,NULL,NULL);
 IF NOT beta.ui_finish(901,902,t,true,210) THEN RAISE EXCEPTION 'cancel preview'; END IF;
 SELECT status INTO STRICT outcome FROM beta.ui_decide(901,902,c,210,true);
 IF outcome<>'removed' THEN RAISE EXCEPTION 'approved cancellation'; END IF;
END $$;
