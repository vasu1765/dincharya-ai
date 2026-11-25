"""Acer-only supervised process rehearsal. Receives two new labelled fixture IDs."""
import json
import subprocess
import sys
import time

db, app = sys.argv[1:3]


def sql(statement):
    return subprocess.check_output(["docker","exec",db,"psql","-XqAt","-v","ON_ERROR_STOP=1",
        "-U","postgres","-d","dincharya_personal_candidate","-c",statement],text=True).strip()


def until(predicate):
    for _ in range(100):
        if predicate():
            return
        time.sleep(.2)
    raise RuntimeError("Timed out waiting for fixture state")


def service():
    return subprocess.Popen(["docker","exec","-i",app,"bash","scripts/supervise-personal-recording.sh",
                             "--recorded-root","/fixture"],stdin=subprocess.PIPE,text=True)


def submit(proc, seq, text=None, decision=None):
    owner={"id":903,"first_name":"Owner","is_bot":False}
    bot={"id":904,"first_name":"Fixture","is_bot":True}
    msg={"message_id":seq,"chat":{"id":903,"type":"private"},"date":int(time.time()),"from":owner}
    if decision:
        proposal, original, action = decision
        msg.update(message_id=int(original),text="Preview")
        msg["from"]=bot
        update={"callback_query":{"id":str(seq),"from":owner,"chat_instance":"fixture","message":msg,
                                  "data":action+"/"+proposal}}
    else:
        msg["text"]=text
        update={"message":msg}
    proc.stdin.write(json.dumps({"update_id":seq,**update})+"\n")
    proc.stdin.flush()


def stop(proc):
    subprocess.run(["docker","exec",app,"touch","/fixture/STOP"],check=True)
    if proc.wait(timeout=15)!=0:
        raise RuntimeError("Unclean shutdown")
    assert sql("SELECT poller OR worker FROM beta.health()")=="f"
    subprocess.run(["docker","exec",app,"rm","/fixture/STOP"],check=True)


def ready():
    return sql("SELECT poller AND worker FROM beta.health()")=="t"


# Verify effective role grants before opening either application connection.
assert sql("""SELECT NOT has_function_privilege('personal_worker','beta.claim()','execute')
 AND NOT has_function_privilege('personal_worker','beta.claim_notice()','execute')
 AND has_function_privilege('personal_worker','beta.recording_claim()','execute')
 AND NOT has_function_privilege('personal_gateway','beta.recording_claim()','execute')
 AND NOT has_table_privilege('personal_gateway','beta.recording_budget','update')""")=="t"
p=service()
until(ready)
competing=subprocess.run(["docker","exec","-i",app,"python","-m","dincharya.personal_service",
                          "--recorded","--root","/fixture"],input="",text=True,timeout=10)
assert competing.returncode!=0
day=sql("SELECT current_date+2")
clock=sql("SELECT to_char((now() AT TIME ZONE 'Asia/Kolkata')+interval '8 hours','HH24:MI')")
quiet_time="09:00" if clock!="09:00" else "10:00"
submit(p,1,"Schedule Practice every day at "+clock+"; 15 minutes and at start")
until(lambda:sql("SELECT count(*) FROM beta.ui_call WHERE state='received'")== "1")
proposal,original=sql("SELECT proposal,message FROM beta.ui_call WHERE method='sendMessage'").split("|")
stop(p)
p=service()
until(ready)
submit(p,2,decision=(proposal,original,"confirm"))
until(lambda:sql("SELECT count(*) FROM beta.ui_call WHERE method='editMessageText' AND state='received'")=="1")
submit(p,3,decision=(proposal,original,"cancel"))
until(lambda:sql("SELECT count(*) FROM beta.ui_call WHERE method='answerCallbackQuery' AND state='received'")=="1")
assert sql("SELECT count(*) FROM beta.proposal WHERE state='active'")=="1"
submit(p,4,"Schedule Quiet on "+day+" at "+quiet_time)
until(lambda:sql("SELECT count(*) FROM beta.ui_call WHERE method='sendMessage' AND state='received'")=="2")
quiet,origin=sql("SELECT u.proposal,u.message FROM beta.ui_call u JOIN beta.proposal p ON p.id=u.proposal WHERE p.title='Quiet' AND u.method='sendMessage'").split("|")
submit(p,5,decision=(quiet,origin,"confirm"))
until(lambda:sql("SELECT count(*) FROM beta.proposal WHERE state='active'")=="2")
assert sql("SELECT count(*) FROM beta.slot s JOIN beta.occurrence o ON o.id=s.occurrence WHERE o.rule='"+quiet+"'")=="0"
assert sql("SELECT array_agg(DISTINCT minutes ORDER BY minutes) FROM beta.slot")=="{0,15}"
sql("UPDATE beta.slot SET due=now()-interval '6 minutes' WHERE id=(SELECT min(id) FROM beta.slot)")
until(lambda:sql("SELECT count(*) FROM beta.slot WHERE state='cancelled'")=="1")
assert sql("SELECT count(*) FROM beta.attempt")=="0"
sql("UPDATE beta.slot SET due=now() WHERE id=(SELECT min(id) FROM beta.slot WHERE state='pending')")
until(lambda:sql("SELECT count(*) FROM beta.attempt WHERE outcome='sent' AND chat=903 AND message>0")=="1")
assert sql("SELECT used FROM beta.recording_budget")=="6"
stop(p)
p=service()
until(ready)
assert sql("SELECT count(*) FROM beta.attempt WHERE outcome='sent'")=="1"
# Simulate a worker lost after reserving its send; the service must quarantine and its supervisor must stop.
sql("UPDATE beta.slot SET state='sending',attempts=1,lease=gen_random_uuid(),deadline=now()-interval '1 second' WHERE id=(SELECT min(id) FROM beta.slot WHERE state='pending')")
assert p.wait(timeout=20)!=0
recovered=service()
assert recovered.wait(timeout=15)!=0
assert sql("SELECT count(*) FROM beta.slot WHERE state='uncertain'")=="1"
assert sql("SELECT used FROM beta.recording_budget")=="6"
assert sql("SELECT count(*) FROM beta.attempt WHERE outcome='uncertain'")=="1"
assert sql("SET SESSION AUTHORIZATION personal_gateway; SELECT beta.acquire(); SELECT beta.reserve_recording(903,904)").splitlines()==["t","f"]
assert sql("SELECT used FROM beta.recording_budget")=="6"
print("PASS controlled restart, original edit, conflicting callback, ownership, late slot and quarantine stop")
