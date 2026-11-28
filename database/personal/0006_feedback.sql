BEGIN;
DO $$ BEGIN
 IF current_database()<>'dincharya_personal_candidate' OR current_setting('server_version_num')::int/10000<>17
 THEN RAISE EXCEPTION 'personal PG17 required'; END IF;
END $$;
SET LOCAL ROLE personal_executor;

CREATE TABLE beta.lunar_reference (
 lunar_key text NOT NULL, month_kind text NOT NULL CHECK(month_kind IN ('ordinary','adhika')),
 civil_year integer NOT NULL, day date NOT NULL CHECK(extract(year FROM day)=civil_year),
 selection text NOT NULL CHECK(selection IN ('single','first','last')),
 PRIMARY KEY(lunar_key,month_kind,civil_year)
);
-- Accepted Delhi date evidence in prototypes/panchang/historical-references.json.
INSERT INTO beta.lunar_reference VALUES('kartika-amanta-krishna-10','ordinary',2027,date '2027-11-23','single');

CREATE TABLE beta.lunar_schedule (
 rule uuid PRIMARY KEY REFERENCES beta.proposal,
 lunar_key text NOT NULL, month_kind text NOT NULL CHECK(month_kind IN ('ordinary','adhika')),
 annual boolean NOT NULL, basis text NOT NULL CHECK(basis IN ('instant','sunrise')),
 repeated text NOT NULL CHECK(repeated IN ('review','first','last')),
 CHECK(length(lunar_key) BETWEEN 8 AND 64)
);

CREATE FUNCTION beta.ui_draft_lunar(actor bigint, bot_id bigint, req bigint, name text,
 day date, tod time, offsets integer[], key_arg text, kind_arg text, annual_arg boolean,
 basis_arg text, repeat_arg text) RETURNS TABLE(proposal uuid,ticket uuid)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p uuid; t uuid; saved beta.lunar_schedule;
BEGIN
 PERFORM beta.ui_owner(actor,bot_id);
 IF NOT EXISTS(SELECT FROM beta.lunar_reference r WHERE r.lunar_key=key_arg AND r.month_kind=kind_arg
 AND r.day=ui_draft_lunar.day AND (r.selection='single' OR r.selection=repeat_arg))
 THEN RAISE EXCEPTION 'unreviewed Delhi lunar date'; END IF;
 SELECT d.proposal,d.ticket INTO STRICT p,t FROM beta.ui_draft(actor,bot_id,req,name,'once',day,tod,offsets) d;
 IF t IS NOT NULL THEN
   INSERT INTO beta.lunar_schedule VALUES(p,key_arg,kind_arg,annual_arg,basis_arg,repeat_arg);
 END IF;
 SELECT * INTO STRICT saved FROM beta.lunar_schedule WHERE rule=p;
 IF (saved.lunar_key,saved.month_kind,saved.annual,saved.basis,saved.repeated)
    IS DISTINCT FROM (key_arg,kind_arg,annual_arg,basis_arg,repeat_arg)
 THEN RAISE EXCEPTION 'lunar request mismatch'; END IF;
 RETURN QUERY SELECT p,t;
END $$;

CREATE FUNCTION beta.reject_lunar_replace() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF NEW.action='replace' AND EXISTS(SELECT FROM beta.lunar_schedule WHERE rule=NEW.target) THEN
    RAISE EXCEPTION 'cancel the lunar rule before creating a reviewed replacement';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER reject_lunar_replace BEFORE INSERT ON beta.ui_change
 FOR EACH ROW EXECUTE FUNCTION beta.reject_lunar_replace();

CREATE FUNCTION beta.ui_is_lunar(actor bigint, bot_id bigint, key_arg uuid) RETURNS boolean
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT EXISTS(SELECT FROM beta.proposal p JOIN beta.lunar_schedule l ON p.id=l.rule
 WHERE p.epoch=beta.ui_owner(actor,bot_id) AND p.id=key_arg AND p.state='active')
$$;

CREATE FUNCTION beta.project_lunar(p beta.proposal) RETURNS void LANGUAGE sql
SET search_path=pg_catalog,pg_temp AS $$
 WITH eligible AS (
  SELECT (r.day+p.at_time) AT TIME ZONE 'Asia/Kolkata' AS starts
  FROM beta.lunar_schedule l JOIN beta.lunar_reference r USING(lunar_key,month_kind)
  WHERE l.rule=p.id AND l.annual AND p.state='active'
    AND r.day>p.starts AND r.day<=(now() AT TIME ZONE 'Asia/Kolkata')::date+400
    AND (r.selection='single' OR r.selection=l.repeated)
 ), inserted AS (
  INSERT INTO beta.occurrence(rule,starts) SELECT p.id,starts FROM eligible WHERE starts>now()
  ON CONFLICT DO NOTHING RETURNING id,starts
 )
 INSERT INTO beta.slot(occurrence,minutes,due)
 SELECT id,x,starts-x*interval '1 minute' FROM inserted CROSS JOIN unnest(p.offsets) x
 WHERE starts-x*interval '1 minute'>now()
$$;

CREATE OR REPLACE FUNCTION beta.roll_forward() RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p beta.proposal;
BEGIN
 IF NOT beta.owned('personal_worker') OR NOT EXISTS(SELECT FROM beta.authority WHERE enabled FOR SHARE)
 THEN RAISE EXCEPTION 'worker fenced'; END IF;
 FOR p IN SELECT r.* FROM beta.proposal r JOIN beta.authority a ON a.epoch=r.epoch
          WHERE r.state='active' ORDER BY r.id FOR UPDATE OF r LOOP
   PERFORM beta.project(p);
   PERFORM beta.project_lunar(p);
 END LOOP;
END $$;

CREATE OR REPLACE FUNCTION beta.ui_rules(actor bigint,bot_id bigint) RETURNS TABLE(id uuid,title text,frequency text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE ep uuid;
BEGIN
 ep:=beta.ui_owner(actor,bot_id);
 RETURN QUERY SELECT p.id,p.title,CASE WHEN l.annual THEN 'lunar annual' WHEN l.rule IS NOT NULL THEN 'lunar once'
 ELSE p.frequency END FROM beta.proposal p LEFT JOIN beta.lunar_schedule l ON l.rule=p.id
 WHERE p.epoch=ep AND p.state='active' ORDER BY p.starts,p.at_time,p.id LIMIT 100;
END $$;

CREATE FUNCTION beta.ui_upcoming(actor bigint,bot_id bigint,first_day date,last_day date)
RETURNS TABLE(title text,starts timestamptz)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE ep uuid;
BEGIN
 ep:=beta.ui_owner(actor,bot_id);
 IF first_day IS NULL OR last_day IS NULL OR last_day-first_day NOT BETWEEN 0 AND 30
 THEN RAISE EXCEPTION 'invalid schedule window'; END IF;
 RETURN QUERY SELECT p.title,o.starts FROM beta.occurrence o JOIN beta.proposal p ON p.id=o.rule
 WHERE p.epoch=ep AND p.state='active' AND o.enabled AND o.starts>clock_timestamp()
 AND (o.starts AT TIME ZONE 'Asia/Kolkata')::date BETWEEN first_day AND last_day
 ORDER BY o.starts,o.id LIMIT 16;
END $$;

CREATE FUNCTION beta.ui_status(actor bigint,bot_id bigint)
RETURNS TABLE(pending bigint,uncertain bigint,ui_unsettled bigint)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM beta.ui_owner(actor,bot_id);
 RETURN QUERY SELECT h.pending,h.uncertain,h.ui_unsettled FROM beta.health() h;
END $$;

CREATE TABLE beta.llm_spend (
 epoch uuid PRIMARY KEY REFERENCES beta.live_release,
 max_calls integer NOT NULL, max_cost integer NOT NULL, per_call integer NOT NULL,
 calls integer NOT NULL DEFAULT 0, reserved integer NOT NULL DEFAULT 0
);
CREATE FUNCTION beta.reserve_model(actor bigint,bot_id bigint,pin text,call_limit integer,cost_limit integer,unit_cost integer)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE id uuid;
BEGIN
 id:=beta.ui_owner(actor,bot_id);
 IF call_limit IS NULL OR cost_limit IS NULL OR unit_cost IS NULL
 OR call_limit NOT BETWEEN 1 AND 500 OR unit_cost NOT BETWEEN 1 AND cost_limit
 OR cost_limit NOT BETWEEN 1 AND 10000000 OR NOT EXISTS(
  SELECT FROM beta.live_release r WHERE r.epoch=id AND r.digest=pin AND r.profile='daily'
   AND r.started AND clock_timestamp()>=r.opens AND clock_timestamp()<r.closes)
 THEN RETURN false; END IF;
 INSERT INTO beta.llm_spend(epoch,max_calls,max_cost,per_call)
 VALUES(id,call_limit,cost_limit,unit_cost) ON CONFLICT DO NOTHING;
 UPDATE beta.llm_spend SET calls=calls+1,reserved=reserved+unit_cost
 WHERE epoch=id AND max_calls=call_limit AND max_cost=cost_limit AND per_call=unit_cost
 AND calls<call_limit AND reserved+unit_cost<=cost_limit;
 RETURN FOUND;
END $$;
REVOKE ALL ON FUNCTION beta.reserve_model(bigint,bigint,text,integer,integer,integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION beta.reserve_model(bigint,bigint,text,integer,integer,integer) TO personal_gateway;
GRANT SELECT ON beta.llm_spend TO personal_backup;

REVOKE ALL ON FUNCTION beta.ui_draft_lunar(bigint,bigint,bigint,text,date,time,integer[],text,text,boolean,text,text),
 beta.ui_is_lunar(bigint,bigint,uuid), beta.ui_upcoming(bigint,bigint,date,date), beta.ui_status(bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION beta.ui_draft_lunar(bigint,bigint,bigint,text,date,time,integer[],text,text,boolean,text,text),
 beta.ui_is_lunar(bigint,bigint,uuid), beta.ui_upcoming(bigint,bigint,date,date), beta.ui_status(bigint,bigint) TO personal_gateway;
GRANT SELECT ON beta.lunar_reference,beta.lunar_schedule TO personal_backup;
COMMIT;
