'use strict';
// Synthetic credentials and request bodies on stdin only; no raw error output.
const fs=require('node:fs');
const origin='http://127.0.0.1:5678';
async function main(input){
  async function rest(path,method,body,cookie){
    const r=await fetch(origin+'/rest/'+path,{method,headers:{'content-type':'application/json',...(cookie?{cookie}:{})},
      body:JSON.stringify(body),signal:AbortSignal.timeout(15000)});
    if(!r.ok)throw Error('API failure');return {data:(await r.json()).data,cookie:r.headers.get('set-cookie')};
  }
  if(input.action==='bootstrap'){
    const {password}=input;
    const session=await rest('owner/setup','POST',{email:'synthetic@example.invalid',firstName:'Synthetic',lastName:'Test',password});
    const cookie=session.cookie.split(';')[0];
    const saved=await rest('workflows','POST',input.workflow,cookie);
    await rest('workflows/'+saved.data.id+'/activate','POST',{versionId:saved.data.versionId},cookie);
    return {id:saved.data.id};
  }
  if(input.action==='request'){
    const r=await fetch(origin+'/webhook/synthetic-lunar-e2e',{method:'POST',headers:{'content-type':'application/json'},
      body:JSON.stringify(input.body),signal:AbortSignal.timeout(45000)});
    if(!r.ok)throw Error('Webhook failure');return await r.json();
  }
  throw Error('Unknown action');
}
main(JSON.parse(fs.readFileSync(0,'utf8'))).then(v=>process.stdout.write(JSON.stringify(v))).catch(()=>{
  process.stderr.write('Synthetic n8n operation failed\n');process.exitCode=1;
});
