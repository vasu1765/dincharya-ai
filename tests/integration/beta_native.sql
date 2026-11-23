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
SET SESSION AUTHORIZATION beta_operator;
DO $$ DECLARE observation_row record; action uuid:=gen_random_uuid(); evidence uuid:=gen_random_uuid(); auth uuid:=gen_random_uuid();
BEGIN
 SELECT * INTO STRICT observation_row FROM beta.inspect_uncertain();
 IF NOT beta.reconcile(action,observation_row.slot_id,observation_row.observation,101,235,evidence,auth,'observed synthetic receipt',true)
 THEN RAISE EXCEPTION 'confirmed receipt missing'; END IF;
 IF beta.reconcile(action,observation_row.slot_id,observation_row.observation,101,235,evidence,auth,'observed synthetic receipt',true)
 THEN RAISE EXCEPTION 'duplicate reconciliation'; END IF;
END $$;
RESET SESSION AUTHORIZATION;
