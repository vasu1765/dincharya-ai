'use strict';
// Runs only inside n8n-test. Input/output protocol; never print response bodies/errors.
const fs = require('node:fs');
const { createRequire } = require('node:module');
const nativeRequire = createRequire('/usr/local/lib/node_modules/n8n/package.json');
const { parse: parseFlatted } = nativeRequire('flatted');
const origin = 'http://127.0.0.1:5678/rest/';
class ApiFailure extends Error {}

async function main(input) {
  if (nativeRequire('./package.json').version !== '2.47.3' ||
      nativeRequire('n8n-nodes-base/package.json').version !== '2.47.2' || process.getuid() !== 1000) {
    throw Error('Unexpected runtime version or UID');
  }
  let cookie;
  async function api(path, method = 'GET', body, authenticated = true) {
    const response = await fetch(origin + path, {
      method, headers: { 'content-type': 'application/json', ...(authenticated ? { cookie } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(10000),
    });
    if (!response.ok) throw new ApiFailure('Synthetic API ' + method + ' ' +
      path.split('/')[0] + ' failed with HTTP ' + response.status);
    const value = await response.json();
    return { value: value.data, cookie: response.headers.get('set-cookie') };
  }
  const owner = { email: 'synthetic@example.invalid', firstName: 'Synthetic',
    lastName: 'Test', password: input.password };
  const sessionPath = '/tmp/synthetic-api-session.json';
  if (input.action !== 'bootstrap' && fs.existsSync(sessionPath)) {
    cookie = JSON.parse(fs.readFileSync(sessionPath, 'utf8')).cookie;
  } else {
    const session = input.action === 'bootstrap'
      ? await api('owner/setup', 'POST', owner, false)
      : await api('login', 'POST', { emailOrLdapLoginId: owner.email, password: owner.password }, false);
    if (!session.cookie) throw Error('Missing synthetic session');
    cookie = session.cookie.split(';')[0];
    fs.writeFileSync(sessionPath, JSON.stringify({ cookie }), { mode: 0o600 });
  }

  if (input.action === 'bootstrap') {
    const ids = {};
    for (const name of ['manual-smoke', 'scheduler-state']) {
      const fixture = JSON.parse(fs.readFileSync('/opt/synthetic/fixtures/' + name + '.json', 'utf8'));
      const { value: saved } = await api('workflows', 'POST', fixture);
      const { value: stored } = await api('workflows/' + encodeURIComponent(saved.id));
      ids[name] = saved.id;
      if (name === 'scheduler-state') {
        // The pinned create API drops staticData. Prepare the unchanged synthetic
        // fixture for the native CLI import contract, targeting only this new ID.
        const native = JSON.parse(JSON.stringify(fixture));
        native.name = 'Synthetic M2C native cadence gate';
        native.nodes[0].parameters.rule.interval = [{ field: 'minutes', minutesInterval: 7 }];
        native.staticData['node:Synthetic schedule'].recurrenceRuleSignatures = ['minutes:7'];
        const { value: nativeSaved } = await api('workflows', 'POST', native);
        ids['native-gate'] = nativeSaved.id;
        fs.writeFileSync('/tmp/synthetic-scheduler-import.json',
          JSON.stringify([{ ...fixture, id: saved.id }, { ...native, id: nativeSaved.id }]), { mode: 0o600 });
        return { ids, importedState: stored.staticData, nativeState: native.staticData };
      }
    }
  } else if (input.action === 'activate' || input.action === 'activate-native') {
    const path = 'workflows/' + encodeURIComponent(input.id);
    const { value: stored } = await api(path);
    if (input.action === 'activate') {
      stored.nodes.find(n => n.type === 'n8n-nodes-base.scheduleTrigger').parameters.rule.interval =
        [{ field: 'seconds', secondsInterval: 5 }];
    }
    const { value: updated } = await api(path, 'PATCH', {
      nodes: stored.nodes, connections: stored.connections, settings: stored.settings,
      staticData: stored.staticData,
    });
    await api(path + '/activate', 'POST', { versionId: updated.versionId });
    return { activated: true };
  } else if (input.action === 'execution') {
    const { value: execution } = await api('executions/' + encodeURIComponent(input.id));
    const data = typeof execution.data === 'string' ? parseFlatted(execution.data) : execution.data;
    return { data };
  } else if (input.action === 'deactivate') {
    await api('workflows/' + encodeURIComponent(input.id) + '/deactivate', 'POST', {});
    return { deactivated: true };
  }
  throw Error('Unknown action');
}

main(JSON.parse(fs.readFileSync(0, 'utf8'))).then(result => {
  process.stdout.write(JSON.stringify(result));
}).catch(error => {
  process.stderr.write((error instanceof ApiFailure ? error.message : 'Synthetic API operation failed') + '\n');
  process.exitCode = 1;
});
