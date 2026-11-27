-- Optional UX delta for a fresh synthetic personal-schema rehearsal only.
BEGIN;
DO $$ BEGIN
 IF current_database()<>'dincharya_beta_rehearsal' OR current_setting('server_version_num')::int/10000<>17
 THEN RAISE EXCEPTION 'Fresh PG17 rehearsal required'; END IF;
END $$;
CREATE ROLE daily_gateway NOLOGIN;
SET LOCAL ROLE beta_executor;
CREATE TABLE beta.ui_bot(singleton boolean PRIMARY KEY CHECK(singleton),
 bot bigint NOT NULL CHECK(bot>0 AND bot<>101));
CREATE TABLE beta.ui_call(
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), epoch uuid NOT NULL, proposal uuid REFERENCES beta.proposal, reply_update bigint UNIQUE CHECK(reply_update>0),
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
 SELECT a.epoch INTO STRICT epoch_id FROM beta.authority a,beta.ui_bot b
 WHERE a.recipient=actor AND b.bot=bot_id AND session_user='daily_gateway' FOR SHARE OF a,b;
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
CREATE FUNCTION beta.ui_decide(actor bigint,bot_id bigint,p uuid,origin bigint,accept boolean)
RETURNS TABLE(status text,method text,ticket uuid,title text,day date,tod time)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE r beta.proposal; epoch_id uuid; m text; t uuid; outcome text;
BEGIN
 epoch_id:=beta.ui_owner(actor,bot_id);
 SELECT * INTO r FROM beta.proposal WHERE id=p AND epoch=epoch_id FOR UPDATE;
 IF NOT FOUND OR accept IS NULL OR NOT EXISTS(SELECT FROM beta.ui_call c WHERE c.proposal=p
 AND c.method='sendMessage' AND c.state='received' AND c.chat=actor AND c.message=origin)
 THEN RETURN; END IF;
 IF r.state='pending' THEN
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
   outcome:=r.state;
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
GRANT USAGE ON SCHEMA beta TO daily_gateway;
GRANT EXECUTE ON FUNCTION beta.ui_reply(bigint,bigint,bigint),beta.ui_draft(bigint,bigint,bigint,text,text,date,time,integer[]),
 beta.ui_decide(bigint,bigint,uuid,bigint,boolean),beta.ui_finish(bigint,bigint,uuid,boolean,bigint) TO daily_gateway;
COMMIT;
