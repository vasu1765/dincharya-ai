-- Scoped daily UI and separately approved civil changes.
BEGIN;
DO $$ BEGIN
 IF current_database()<>'dincharya_personal_candidate' OR current_setting('server_version_num')::int/10000<>17
 THEN RAISE EXCEPTION 'Fresh PG17 rehearsal required'; END IF;
END $$;

SET LOCAL ROLE personal_executor;
CREATE TABLE beta.ui_change(
 proposal uuid PRIMARY KEY REFERENCES beta.proposal, target uuid NOT NULL REFERENCES beta.proposal,
 revision integer NOT NULL, action text NOT NULL CHECK(action IN ('cancel','replace')),
 outcome text CHECK(outcome IN ('cancelled','active','expired','conflict','kept','removed','replaced'))
);
CREATE TABLE beta.ui_call(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), reserved_at timestamptz NOT NULL DEFAULT clock_timestamp(), epoch uuid NOT NULL, proposal uuid REFERENCES beta.proposal, reply_update bigint UNIQUE CHECK(reply_update>0),
 CHECK ((proposal IS NULL)=(reply_update IS NOT NULL)), CHECK(reply_update IS NULL OR method='sendMessage'),
 method text NOT NULL CHECK(method IN ('sendMessage','editMessageText','answerCallbackQuery')),
 state text NOT NULL DEFAULT 'reserved' CHECK(state IN ('reserved','received','uncertain')),
 chat bigint, message bigint, UNIQUE(proposal,method),
 CHECK ((chat IS NULL)=(message IS NULL)), CHECK(message IS NULL OR message>0)
);
CREATE UNIQUE INDEX ui_preview_origin ON beta.ui_call(chat,message) WHERE method='sendMessage';
CREATE FUNCTION beta.ui_owner(actor bigint, bot_id bigint) RETURNS uuid
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE epoch_id uuid;
BEGIN
 SELECT a.epoch INTO STRICT epoch_id FROM beta.authority a
 WHERE a.recipient=actor AND a.bot=bot_id AND a.enabled AND beta.owned('personal_gateway') FOR SHARE OF a;
 RETURN epoch_id;
END $$;
CREATE FUNCTION beta.ui_reply(actor bigint,bot_id bigint,req bigint) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE t uuid; epoch_id uuid;
BEGIN
 epoch_id:=beta.ui_owner(actor,bot_id);
 INSERT INTO beta.ui_call(epoch,reply_update,method) VALUES(epoch_id,req,'sendMessage') ON CONFLICT DO NOTHING RETURNING id INTO t;
 RETURN t;
END $$;
CREATE FUNCTION beta.ui_draft(actor bigint,bot_id bigint,req bigint,title_arg text,freq text,
 day date,tod time,offs integer[]) RETURNS TABLE(proposal uuid,ticket uuid)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p uuid; t uuid; epoch_id uuid;
BEGIN
 epoch_id:=beta.ui_owner(actor,bot_id);
 p:=beta.draft(actor,req,title_arg,freq,day,tod,offs);
 INSERT INTO beta.ui_call(epoch,proposal,method) VALUES(epoch_id,p,'sendMessage') ON CONFLICT DO NOTHING RETURNING id INTO t;
 RETURN QUERY SELECT p,t;
END $$;
CREATE FUNCTION beta.ui_change_draft(actor bigint,bot_id bigint,req bigint,target_id uuid,op text,
 title_arg text,freq text,day date,tod time,offs integer[]) RETURNS TABLE(proposal uuid,ticket uuid,label text)
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE target beta.proposal; p uuid; t uuid; ep uuid; binding beta.ui_change;
BEGIN
 ep:=beta.ui_owner(actor,bot_id);
 SELECT * INTO target FROM beta.proposal WHERE id=target_id AND epoch=ep AND state='active' FOR UPDATE;
 IF NOT FOUND OR op IS NULL OR op NOT IN ('cancel','replace') THEN RETURN; END IF;
 IF op='cancel' THEN
   title_arg:=target.title; freq:=target.frequency; day:=target.starts; tod:=target.at_time; offs:=target.offsets;
 END IF;
 SELECT d.proposal,d.ticket INTO STRICT p,t FROM beta.ui_draft(actor,bot_id,req,title_arg,freq,day,tod,offs) d;
 IF t IS NOT NULL THEN
   INSERT INTO beta.ui_change VALUES(p,target.id,target.revision,op,NULL);
 ELSE
   SELECT * INTO STRICT binding FROM beta.ui_change WHERE ui_change.proposal=p AND ui_change.target=target_id AND action=op;
 END IF;
 RETURN QUERY SELECT p,t,target.title;
END $$;
CREATE FUNCTION beta.ui_rules(actor bigint,bot_id bigint) RETURNS TABLE(id uuid,title text,frequency text)
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE ep uuid;
BEGIN
 ep:=beta.ui_owner(actor,bot_id);
 RETURN QUERY SELECT p.id,p.title,p.frequency FROM beta.proposal p WHERE p.epoch=ep AND p.state='active'
 ORDER BY p.starts,p.at_time,p.id LIMIT 25;
END $$;
CREATE FUNCTION beta.ui_decide(actor bigint,bot_id bigint,p uuid,origin bigint,accept boolean)
RETURNS TABLE(status text,method text,ticket uuid,title text,day date,tod time)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
<<decision>>
DECLARE r beta.proposal; epoch_id uuid; m text; t uuid; outcome text; ch beta.ui_change; target beta.proposal; change_token uuid;
BEGIN
 epoch_id:=beta.ui_owner(actor,bot_id);
 SELECT * INTO r FROM beta.proposal WHERE id=p AND epoch=epoch_id FOR UPDATE;
 IF NOT FOUND OR accept IS NULL OR NOT EXISTS(SELECT FROM beta.ui_call c WHERE c.proposal=p
 AND c.method='sendMessage' AND c.state='received' AND c.chat=actor AND c.message=origin)
 THEN RETURN; END IF;
 SELECT * INTO ch FROM beta.ui_change WHERE ui_change.proposal=p;
 IF r.state='pending' AND ch.proposal IS NOT NULL THEN
   SELECT * INTO STRICT target FROM beta.proposal WHERE id=ch.target FOR UPDATE;
   outcome:='expired';
   IF r.expires>clock_timestamp() AND target.epoch=epoch_id AND target.revision=ch.revision AND target.state='active' THEN
     IF NOT accept THEN outcome:='kept';
     ELSIF ch.action='cancel' OR (r.starts+r.at_time) AT TIME ZONE 'Asia/Kolkata'>clock_timestamp() THEN
       BEGIN
         change_token:=beta.review_change(actor,r.request_id,target.id,'cancel');
         PERFORM beta.apply_change(actor,change_token);
         outcome:=CASE WHEN ch.action='replace' THEN beta.decide(actor,p,true) ELSE 'cancelled' END;
         IF ch.action='replace' AND outcome<>'active' THEN RAISE EXCEPTION 'stale replacement' USING ERRCODE='P2001'; END IF;
       EXCEPTION WHEN unique_violation THEN outcome:='conflict'; WHEN SQLSTATE 'P2001' THEN outcome:='expired';
       END;
     END IF;
   END IF;
   IF outcome<>'active' THEN UPDATE beta.proposal SET state=CASE WHEN outcome='cancelled' THEN 'cancelled' ELSE 'expired' END WHERE id=p; END IF;
   outcome:=CASE outcome WHEN 'active' THEN 'replaced' WHEN 'cancelled' THEN 'removed' ELSE outcome END;
   UPDATE beta.ui_change SET outcome=decision.outcome WHERE ui_change.proposal=p;
   m:='editMessageText';
 ELSIF r.state='pending' THEN
   IF r.expires<=clock_timestamp() OR (r.starts+r.at_time) AT TIME ZONE 'Asia/Kolkata'<=clock_timestamp() THEN
     UPDATE beta.proposal SET state='expired' WHERE id=p;
     outcome:='expired';
   ELSE
     BEGIN
       outcome:=beta.decide(actor,p,accept);
     EXCEPTION WHEN unique_violation THEN
       UPDATE beta.proposal SET state='expired' WHERE id=p;
       outcome:='conflict';
     END;
   END IF;
   m:='editMessageText';
 ELSE
   outcome:=coalesce(ch.outcome,r.state);
   m:='answerCallbackQuery';
 END IF;
 INSERT INTO beta.ui_call(epoch,proposal,method) VALUES(epoch_id,p,m) ON CONFLICT DO NOTHING RETURNING id INTO t;
 RETURN QUERY SELECT outcome,m,t,r.title,r.starts,r.at_time;
END $$;
CREATE FUNCTION beta.ui_finish(actor bigint,bot_id bigint,t uuid,ok boolean,msg bigint) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE c beta.ui_call; valid boolean; epoch_id uuid;
BEGIN
 epoch_id:=beta.ui_owner(actor,bot_id);
 SELECT u.* INTO c FROM beta.ui_call u LEFT JOIN beta.proposal p ON p.id=u.proposal
 WHERE u.id=t AND u.epoch=epoch_id AND (p.epoch=epoch_id OR u.reply_update IS NOT NULL) AND u.state='reserved' FOR UPDATE OF u;
 IF NOT FOUND THEN RETURN false; END IF;
 valid:=ok IS TRUE AND CASE c.method WHEN 'answerCallbackQuery' THEN msg IS NULL
 WHEN 'editMessageText' THEN EXISTS(SELECT FROM beta.ui_call WHERE proposal=c.proposal AND method='sendMessage'
 AND state='received' AND chat=actor AND message=msg) ELSE msg IS NOT NULL AND msg>0 END;
 UPDATE beta.ui_call SET state=CASE WHEN valid THEN 'received' ELSE 'uncertain' END,
 chat=CASE WHEN valid AND msg IS NOT NULL THEN actor END,message=CASE WHEN valid THEN msg END WHERE id=t;
 RETURN valid;
END $$;
REVOKE ALL ON FUNCTION beta.ui_owner(bigint,bigint),beta.ui_reply(bigint,bigint,bigint),beta.ui_draft(bigint,bigint,bigint,text,text,date,time,integer[]),
 beta.ui_decide(bigint,bigint,uuid,bigint,boolean),beta.ui_finish(bigint,bigint,uuid,boolean,bigint) FROM PUBLIC;
GRANT USAGE ON SCHEMA beta TO personal_gateway;
GRANT EXECUTE ON FUNCTION beta.ui_rules(bigint,bigint),beta.ui_change_draft(bigint,bigint,bigint,uuid,text,text,text,date,time,integer[]),beta.ui_reply(bigint,bigint,bigint),beta.ui_draft(bigint,bigint,bigint,text,text,date,time,integer[]),
 beta.ui_decide(bigint,bigint,uuid,bigint,boolean),beta.ui_finish(bigint,bigint,uuid,boolean,bigint) TO personal_gateway;
COMMIT;
