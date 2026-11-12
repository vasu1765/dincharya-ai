'use strict';
// Synthetic internal HTTP service only. No external calls, credentials or payload logs.
const http = require('node:http');
const counts = { telegram: 0, ollama: 0 };
const server = http.createServer((request, response) => {
  const reply = (status, value) => {
    response.writeHead(status, { 'content-type': 'application/json' });
    response.end(JSON.stringify(value));
  };
  if (request.method === 'GET' && request.url === '/health') return reply(200, { ok: true });
  if (request.method === 'GET' && request.url === '/counts') return reply(200, counts);
  const target = request.url === '/telegram/sendMessage' ? 'telegram' :
    request.url === '/ollama/api/chat' ? 'ollama' : null;
  if (request.method !== 'POST' || target === null) return reply(404, { ok: false });
  let chunks = [];
  let size = 0;
  let rejected = false;
  request.on('data', (chunk) => {
    size += chunk.length;
    if (size > 16384) {
      if (!rejected) reply(413, { ok: false });
      rejected = true;
      chunks = [];
    } else if (!rejected) chunks.push(chunk);
  });
  request.on('end', () => {
    if (rejected) return;
    try { JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch { return reply(400, { ok: false }); }
    counts[target] += 1;
    if (target === 'telegram') return reply(200, { ok: true, result: { message_id: counts.telegram } });
    return reply(200, { done: true, message: { role: 'assistant', content: 'synthetic-response' } });
  });
  request.on('error', () => { if (!response.writableEnded) reply(400, { ok: false }); });
});
server.requestTimeout = 15000;
server.headersTimeout = 10000;
server.maxHeadersCount = 32;
server.listen(8080, '0.0.0.0');
