// EmbyFlow Telegram setup, stage 1. Contains no credentials.
// The bot token is configured only as the TELEGRAM_BOT_TOKEN Worker secret.
const headers = {
  'Content-Type': 'text/html; charset=utf-8',
  'Cache-Control': 'no-store',
  'Content-Security-Policy': "default-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
};
const page = content => new Response(
  '<!doctype html><html lang="de"><meta charset="utf-8">' +
  '<meta name="viewport" content="width=device-width,initial-scale=1">' +
  '<title>EmbyFlow Einrichtung</title><body><h1>EmbyFlow Support</h1>' + content + '</body></html>',
  { headers });
const escape = value => String(value).replace(/[&<>"']/g,
  char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);

async function boundedBody(request) {
  if (!request.body) return '';
  const reader = request.body.getReader();
  const chunks = [];
  let size = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > 4096) {
      await reader.cancel();
      throw new Error('body limit');
    }
    chunks.push(value);
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  return new TextDecoder().decode(bytes);
}

async function sameSecret(a, b) {
  const digest = text => crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  const [left, right] = await Promise.all([digest(a), digest(b)]);
  const x = new Uint8Array(left), y = new Uint8Array(right);
  let difference = 0;
  for (let i = 0; i < x.length; i++) difference |= x[i] ^ y[i];
  return difference === 0;
}

export async function handle(request, env, fetcher = fetch) {
  const url = new URL(request.url);
  const token = env.TELEGRAM_BOT_TOKEN;
  if (request.method === 'GET' && url.pathname === '/') {
    if (!token) return page('<h2>Bot-Token fehlt</h2><p>Bitte TELEGRAM_BOT_TOKEN als Secret speichern.</p>');
    return page('<h2>Telegram-Gruppe ermitteln</h2>' +
      '<p>Schreibe zuerst in deine Telegram-Supportgruppe:</p>' +
      '<pre>/support@EmbyFlowSupport6893Bot</pre>' +
      '<form method="post" action="/groups">' +
      '<p><label>Neuer Bot-Token zur Freigabe:<br>' +
      '<input type="password" name="token" required autocomplete="off" size="50"></label></p>' +
      '<button type="submit">Gruppe ermitteln</button></form>' +
      '<p>Der Token wird verborgen eingegeben. Die Gruppenabfrage sendet keine Nachricht.</p>');
  }
  if (url.pathname !== '/groups' || request.method !== 'POST')
    return new Response('Nicht verfuegbar', { status: 404, headers: { 'Cache-Control': 'no-store' } });
  if (!token) return page('<h2>Bot-Token fehlt.</h2>');
  const origin = request.headers.get('Origin');
  if (origin && origin !== url.origin) return new Response('Nicht erlaubt', { status: 403 });
  try {
    const input = new URLSearchParams(await boundedBody(request)).get('token') || '';
    if (!input || !await sameSecret(input, token))
      return page('<h2>Token stimmt nicht.</h2><p>Bitte den neuesten Token verwenden.</p><a href="/">Zurueck</a>');
    const response = await fetcher('https://api.telegram.org/bot' + token + '/getUpdates', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ timeout: 0, limit: 100 }), signal: AbortSignal.timeout(10000),
    });
    if (!response.ok) return page('<h2>Telegram-Abfrage fehlgeschlagen.</h2><p>Token und Bot-Einrichtung pruefen.</p>');
    const data = await response.json();
    if (!data.ok || !Array.isArray(data.result)) return page('<h2>Telegram-Abfrage fehlgeschlagen.</h2>');
    const groups = new Map();
    for (const update of data.result) {
      const chat = (update.message || update.my_chat_member || {}).chat;
      if (chat && ['group', 'supergroup'].includes(chat.type) && /^-\d+$/.test(String(chat.id)))
        groups.set(String(chat.id), String(chat.title || 'Gruppe'));
    }
    if (!groups.size) return page('<h2>Noch keine Gruppe gefunden.</h2>' +
      '<p>In der Gruppe /support@EmbyFlowSupport6893Bot senden und erneut versuchen.</p><a href="/">Zurueck</a>');
    return page('<h2>Gefundene Gruppen</h2>' + Array.from(groups, ([id, title]) =>
      '<h3>' + escape(title) + '</h3><p>Gruppen-ID:</p><pre>' + escape(id) + '</pre>').join('') +
      '<p>Die Gruppen-ID benoetigen wir als naechsten Einrichtungsschritt.</p>');
  } catch {
    return page('<h2>Abfrage nicht moeglich.</h2><p>Bitte spaeter erneut versuchen.</p><a href="/">Zurueck</a>');
  }
}

export default { fetch(request, env) { return handle(request, env); } };
