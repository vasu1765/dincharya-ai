\set ON_ERROR_STOP on
DO $$ BEGIN
 IF (SELECT count(*) FROM beta.proposal WHERE state='cancelled')<>1
 OR (SELECT count(*) FROM beta.occurrence)<>1 OR (SELECT count(*) FROM beta.slot WHERE state='cancelled')<>1
 THEN RAISE EXCEPTION 'relay history mismatch'; END IF;
END $$;
SELECT beta.draft(101,20,'Receipt fixture','once',current_date+2,'14:30',ARRAY[0,15]) AS token \gset
SELECT beta.decide(101,:'token',true);
UPDATE beta.slot SET due=now()-interval '1 minute' WHERE state='pending';
SET ROLE beta_worker;
DO $$ DECLARE s record; t record;
BEGIN
 IF has_table_privilege(current_user,'beta.slot','UPDATE') OR has_function_privilege(current_user,'beta.decide(bigint,uuid,boolean)','EXECUTE')
 THEN RAISE EXCEPTION 'worker privilege leak'; END IF;
 SELECT * INTO STRICT s FROM beta.claim();
 IF EXISTS(SELECT 1 FROM beta.claim()) THEN RAISE EXCEPTION 'parallel send'; END IF;
 BEGIN
  PERFORM beta.finish(s.slot_id,s.token,'sent',101,NULL);
  RAISE EXCEPTION 'unpaired send';
 EXCEPTION WHEN check_violation THEN NULL; END;
 IF NOT beta.finish(s.slot_id,s.token,'sent',101,234) THEN RAISE EXCEPTION 'receipt failed'; END IF;
 IF beta.finish(s.slot_id,s.token,'sent',101,234)
 THEN RAISE EXCEPTION 'receipt replay'; END IF;
 SELECT * INTO STRICT t FROM beta.claim();
 IF NOT beta.finish(t.slot_id,t.token,'uncertain',NULL,NULL) THEN RAISE EXCEPTION 'uncertain failed'; END IF;
 IF EXISTS(SELECT 1 FROM beta.claim())
 THEN RAISE EXCEPTION 'uncertain replay'; END IF;
END $$;
RESET ROLE;
SELECT beta.draft(101,21,'Restore fixture','once',current_date+2,'16:30',ARRAY[]::int[]) AS stale \gset
SELECT beta.fence_restore();
DO $$ BEGIN
 IF (SELECT count(*) FROM beta.slot WHERE state='sent' AND chat=101 AND message=234)<>1
 OR (SELECT count(*) FROM beta.slot WHERE state='uncertain')<>1 OR (SELECT count(*) FROM beta.attempt)<>2
 OR NOT EXISTS(SELECT 1 FROM beta.proposal WHERE request_id=21 AND state='expired')
 THEN RAISE EXCEPTION 'restore ledger mismatch'; END IF;
END $$;
-- Fixture authority independently provisions observations and single-use grants.
INSERT INTO beta.receipt_evidence(id,epoch,slot_id,chat,message,digest,delivered_at,verified)
 SELECT md5('proof-'||n)::uuid,a.epoch,u.slot_id,101,235,
 encode(sha256(convert_to('synthetic paired receipt 101/235','UTF8')),'hex'),now(),n<>3
 FROM beta.inspect_uncertain() u CROSS JOIN beta.authority a CROSS JOIN generate_series(1,5) n;
INSERT INTO beta.reconcile_permit(id,action_id,operator_oid,epoch,slot_id,evidence,observed,reason,approved,expires)
 SELECT md5('permit-'||n)::uuid,md5('action-'||n)::uuid,'beta_operator'::regrole::oid,
 a.epoch,u.slot_id,md5('proof-'||n)::uuid,u.observation,'fixture review',n<>4,
 now()+CASE WHEN n=2 THEN -interval '1 minute' ELSE interval '10 minutes' END
 FROM beta.inspect_uncertain() u CROSS JOIN beta.authority a CROSS JOIN generate_series(1,5) n;

SET SESSION AUTHORIZATION beta_worker;
DO $$ BEGIN
 BEGIN
   PERFORM beta.reconcile(gen_random_uuid(),1,repeat('0',64),101,235,
     gen_random_uuid(),gen_random_uuid(),'fixture review',true);
   RAISE EXCEPTION 'worker reconciled';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END $$;
RESET SESSION AUTHORIZATION;
SET SESSION AUTHORIZATION beta_operator;
DO $$ DECLARE u record; n int;
BEGIN
 SELECT * INTO STRICT u FROM beta.inspect_uncertain();
 IF has_table_privilege(current_user,'beta.receipt_evidence','INSERT') OR
    has_table_privilege(current_user,'beta.reconcile_permit','INSERT') THEN RAISE EXCEPTION 'issuance privilege leak'; END IF;
 -- absent, expired, unverified, unapproved, wrong recipient, wrong message, reused permit for different action
 FOREACH n IN ARRAY ARRAY[0,2,3,4,5,6,7] LOOP
   BEGIN
     PERFORM beta.reconcile(md5('action-'||CASE WHEN n=6 THEN 5 ELSE n END)::uuid,u.slot_id,u.observation,
       CASE WHEN n=5 THEN 102 ELSE 101 END,CASE WHEN n=6 THEN 236 ELSE 235 END,
       md5('proof-'||least(n,5))::uuid,md5('permit-'||least(n,5))::uuid,'fixture review',true);
     RAISE EXCEPTION 'invalid permit accepted %',n;
   EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 END LOOP;
 BEGIN
   PERFORM beta.reconcile(md5('action-1')::uuid,u.slot_id,repeat('0',64),101,235,
       md5('proof-1')::uuid,md5('permit-1')::uuid,'fixture review',true);
   RAISE EXCEPTION 'obsolete observation accepted';
 EXCEPTION WHEN raise_exception THEN IF SQLERRM<>'stale observation' THEN RAISE; END IF; END;
 IF NOT beta.reconcile(md5('action-1')::uuid,u.slot_id,u.observation,101,235,
   md5('proof-1')::uuid,md5('permit-1')::uuid,'fixture review',true) THEN RAISE EXCEPTION 'valid receipt rejected'; END IF;
 IF beta.reconcile(md5('action-1')::uuid,u.slot_id,u.observation,101,235,
   md5('proof-1')::uuid,md5('permit-1')::uuid,'fixture review',true) THEN RAISE EXCEPTION 'duplicate mutation'; END IF;
 BEGIN
   PERFORM beta.reconcile(md5('action-1')::uuid,u.slot_id,u.observation,101,236,
     md5('proof-1')::uuid,md5('permit-1')::uuid,'fixture review',true);
   RAISE EXCEPTION 'altered replay accepted';
 EXCEPTION WHEN raise_exception THEN IF SQLERRM<>'reconciliation replay mismatch' THEN RAISE; END IF; END;
END $$;
RESET SESSION AUTHORIZATION;
DO $$ BEGIN
 IF (SELECT count(*) FROM beta.resolution)<>1 OR
 (SELECT count(*) FROM beta.slot WHERE state='sent' AND chat=101 AND message=235)<>1
 THEN RAISE EXCEPTION 'reconciliation history mismatch'; END IF;
END $$;
