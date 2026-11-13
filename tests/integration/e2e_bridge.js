'use strict';
// Internal HTTP <-> stdio plumbing ONLY. No scheduling, SQL, delivery or logging.
const http = require('node:http');
const readline = require('node:readline');
const crypto = require('node:crypto');
let key = null, next = 0;
const pending = new Map();
const lines = readline.createInterface({ input: process.stdin });
function reply(res, code, data) {
  res.writeHead(code, {'content-type':'application/json'});res.end(JSON.stringify(data));
}
lines.on('line', line => {
  try {
    const data = JSON.parse(line);
    if (!key) {
      if (!/^[a-f0-9]{64}$/.test(data.key)) throw Error();
      key = data.key;
      server.listen(8081, '0.0.0.0', () => process.stdout.write('{"ready":true}\n'));
    } else if (pending.has(data.id)) {
      const item = pending.get(data.id);pending.delete(data.id);clearTimeout(item.timer);
      reply(item.res, 200, data.result);
    }
  } catch { process.exitCode = 1; server.close(); }
});
const server = http.createServer((req,res) => {
  const supplied = req.headers['x-synthetic-key'];
  if (req.method !== 'POST' || req.url !== '/journey' || typeof supplied !== 'string' ||
      supplied.length !== key.length || !crypto.timingSafeEqual(Buffer.from(supplied),Buffer.from(key)))
    return reply(res,403,{status:'denied'});
  let body='',size=0;
  req.on('data',chunk=>{size+=chunk.length;if(size<=16384)body+=chunk;});
  req.on('end',()=>{
    if(size>16384)return reply(res,413,{status:'denied'});
    try {
      const input=JSON.parse(body),id=++next;
      if(pending.size>=8)return reply(res,503,{status:'busy'});
      const timer=setTimeout(()=>{pending.delete(id);if(!res.writableEnded)reply(res,504,{status:'unknown'});},45000);
      pending.set(id,{res,timer});process.stdout.write(JSON.stringify({id,input})+'\n');
    } catch {reply(res,400,{status:'denied'});}
  });
});
server.requestTimeout=45000;server.headersTimeout=10000;server.maxHeadersCount=32;
lines.on('close',()=>{for(const {res,timer} of pending.values()){clearTimeout(timer);reply(res,503,{status:'unknown'});}server.close();});
