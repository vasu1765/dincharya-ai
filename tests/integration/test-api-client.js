'use strict';
// Offline VM harness: fake filesystem, HTTP and package metadata. No services.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(process.argv[2], 'utf8');

async function invoke(files, action, status = 200) {
  const calls = [];
  let stdout = '', stderr = '';
  const fakeFs = {
    existsSync: path => files.has(path),
    readFileSync: path => path === 0 ? JSON.stringify({ action, id: 'invented-id', password: 'invented' }) : files.get(path),
    writeFileSync: (path, value, options) => { assert.equal(options.mode, 0o600); files.set(path, value); },
  };
  const nativeRequire = name => name === 'flatted' ? { parse: JSON.parse }
    : { version: name === './package.json' ? '2.47.3' : '2.47.2' };
  const context = {
    require: name => name === 'node:fs' ? fakeFs : { createRequire: () => nativeRequire },
    process: { getuid: () => 1000, stdout: { write: v => { stdout += v; } },
      stderr: { write: v => { stderr += v; } }, exitCode: 0 },
    AbortSignal: { timeout: () => ({}) },
    fetch: async (url, options) => {
      calls.push({ url, method: options.method, cookie: options.headers.cookie });
      return { ok: status === 200, status,
        headers: { get: () => 'synthetic-cookie=value; HttpOnly' },
        json: async () => ({ data: { data: { resultData: { runData: {} } } } }) };
    },
  };
  vm.runInNewContext(source, context);
  for (let i = 0; i < 20; ++i) await new Promise(resolve => setImmediate(resolve));
  return { calls, stdout, stderr, exitCode: context.process.exitCode };
}

(async () => {
  const files = new Map();
  let first = await invoke(files, 'execution');
  assert.equal(first.exitCode, 0);
  assert.equal(first.calls.filter(c => c.url.endsWith('/login')).length, 1);
  assert(files.has('/tmp/synthetic-api-session.json'));
  const second = await invoke(files, 'execution');
  assert.equal(second.exitCode, 0);
  assert.equal(second.calls.filter(c => c.url.endsWith('/login')).length, 0);
  assert.equal(second.calls[0].cookie, 'synthetic-cookie=value');
  files.clear(); // n8n restart discards tmpfs.
  const restarted = await invoke(files, 'execution');
  assert.equal(restarted.calls.filter(c => c.url.endsWith('/login')).length, 1);
  const error = await invoke(files, 'execution', 429);
  assert.equal(error.exitCode, 1);
  assert.match(error.stderr, /HTTP 429/);
  assert.equal(error.stdout, '');
  assert(!error.stderr.includes('invented') && !error.stderr.includes('synthetic-cookie'));
  console.log('Synthetic API session reuse, restart login and sanitized failures passed');
})().catch(() => { process.stderr.write('Offline API regression failed\n'); process.exitCode = 1; });
