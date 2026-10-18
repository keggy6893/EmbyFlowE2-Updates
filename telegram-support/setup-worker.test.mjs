import { test } from 'node:test';
import assert from 'node:assert/strict';
import { handle } from './setup-worker.mjs';

const env = { TELEGRAM_BOT_TOKEN: 'example-test-secret' };
const post = (token = env.TELEGRAM_BOT_TOKEN, headers = {}) => new Request('https://support.example/groups', {
  method: 'POST', headers, body: new URLSearchParams({ token }),
});
test('setup page never exposes configured token and uses password entry', async () => {
  const response = await handle(new Request('https://support.example/'), env);
  const text = await response.text();
  assert(!text.includes(env.TELEGRAM_BOT_TOKEN));
  assert(text.includes('type="password"'));
  assert.equal(response.headers.get('Cache-Control'), 'no-store');
});
test('unauthenticated requests cannot access Telegram regardless of Origin', async () => {
  const fetcher = () => assert.fail('must not contact Telegram');
  assert((await (await handle(post('wrong'), env, fetcher)).text()).includes('Token stimmt nicht'));
  for (const origin of ['null', 'https://other.example']) {
    const response = await handle(post('wrong', { Origin: origin }), env, fetcher);
    assert((await response.text()).includes('Token stimmt nicht'));
  }
});
test('opaque browser Origin is accepted only with the entered valid secret', async () => {
  let calls = 0;
  const fetcher = async () => {
    calls++;
    return Response.json({ ok: true, result: [] });
  };
  const text = await (await handle(post(env.TELEGRAM_BOT_TOKEN, { Origin: 'null' }), env, fetcher)).text();
  assert.equal(calls, 1);
  assert(text.includes('Noch keine Gruppe gefunden'));
});
test('authenticated query returns only escaped group titles and IDs', async () => {
  const fetcher = async (address, options) => {
    assert(address.endsWith('/getUpdates'));
    assert.equal(options.method, 'POST');
    return Response.json({ ok: true, result: [
      { message: { text: 'private message', message_thread_id: 456, from: { username: 'private-person' },
        chat: { id: -100123, type: 'supergroup', title: '<script>group</script>' } } },
      { message: { chat: { id: 123, type: 'private', first_name: 'private-name' } } },
    ] });
  };
  const text = await (await handle(post(), env, fetcher)).text();
  assert(text.includes('-100123'));
  assert(text.includes('<pre>456</pre>'));
  assert(text.includes('&lt;script&gt;'));
  for (const secret of ['private message', 'private-person', 'private-name', env.TELEGRAM_BOT_TOKEN])
    assert(!text.includes(secret));
});
test('upstream exceptions and Telegram error bodies are never reflected', async () => {
  const failing = async () => { throw new Error(env.TELEGRAM_BOT_TOKEN); };
  const text = await (await handle(post(), env, failing)).text();
  assert(!text.includes(env.TELEGRAM_BOT_TOKEN));
  assert(text.includes('Abfrage nicht moeglich'));
  const response = await handle(post(), env, async () => new Response('private error', { status: 401 }));
  assert(!(await response.text()).includes('private error'));
});
test('oversized requests are rejected without contacting Telegram', async () => {
  const text = await (await handle(post('x'.repeat(5000)), env, () => assert.fail('must not fetch'))).text();
  assert(text.includes('Abfrage nicht moeglich'));
});
test('unconfigured worker and unmatched routes remain inert', async () => {
  const text = await (await handle(new Request('https://support.example/'), {})).text();
  assert(text.includes('Bot-Token fehlt'));
  assert.equal((await handle(new Request('https://support.example/report'), env)).status, 404);
});
