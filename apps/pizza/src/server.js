import { createHash, createHmac, randomBytes, timingSafeEqual } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { fileURLToPath } from 'node:url';
import { classifyIp, normalizeIp, parseCidrs } from './network.js';
import { loadCatalog } from './catalog.js';
import { Store } from './store.js';

const publicDir = fileURLToPath(new URL('../public/', import.meta.url));
const files = new Map(await Promise.all(['index.html', 'app.js', 'style.css'].map(async name => [
  `/${name === 'index.html' ? '' : name}`,
  await readFile(`${publicDir}/${name}`),
])));
const types = { '/': 'text/html; charset=utf-8', '/app.js': 'text/javascript; charset=utf-8', '/style.css': 'text/css; charset=utf-8' };
const store = new Store(process.env.PIZZA_DATA_PATH || '/data/orders.json');
await store.load();
let catalog = await loadCatalog(process.env.PIZZA_CATALOG_PATH || '/config/menu.txt');
const boschCidrs = parseCidrs(process.env.PIZZA_BOSCH_CIDRS || '139.15.0.0/16 185.112.176.0/22 192.48.31.0/24 193.108.217.0/24 193.141.57.0/24 194.39.218.0/23 2a03:cc00::/32');
const ownerCidrs = parseCidrs(process.env.PIZZA_OWNER_CIDRS);
const adminPassword = process.env.PIZZA_ADMIN_PASSWORD || '';
const cookieSecret = process.env.PIZZA_COOKIE_SECRET || '';
const paymentBase = String(process.env.PIZZA_PAYMENT_URL || '').replace(/\/$/, '');
const previewMode = process.env.PIZZA_PREVIEW_MODE === 'true';
const deadlineHour = 10;
const deadlineMinute = 30;

const berlinParts = date => Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Europe/Berlin', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
}).formatToParts(date).filter(part => part.type !== 'literal').map(part => [part.type, part.value]));
const today = () => { const p = berlinParts(new Date()); return `${p.year}-${p.month}-${p.day}`; };
const afterDeadline = () => { if (previewMode) return false; const p = berlinParts(new Date()); return Number(p.hour) > deadlineHour || (Number(p.hour) === deadlineHour && Number(p.minute) >= deadlineMinute); };
const safeEqual = (a, b) => { const left = Buffer.from(String(a)); const right = Buffer.from(String(b)); return left.length === right.length && timingSafeEqual(left, right); };
const noIndex = { 'X-Robots-Tag': 'noindex, nofollow, noarchive, nosnippet' };
const json = (res, status, value, headers = {}) => { res.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', ...noIndex, ...headers }); res.end(JSON.stringify(value)); };
const body = async req => { const chunks = []; let size = 0; for await (const chunk of req) { size += chunk.length; if (size > 64_000) throw new Error('Request too large'); chunks.push(chunk); } return JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}'); };
const money = cents => new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(cents / 100);
const total = order => order.items.reduce((sum, line) => sum + line.quantity * line.priceCents, 0);
const hashToken = token => createHash('sha256').update(token).digest('hex');
const signedCookie = () => { const value = String(Date.now()); return `${value}.${createHmac('sha256', cookieSecret).update(value).digest('base64url')}`; };
const isAdmin = req => {
  if (!cookieSecret) return false;
  const token = String(req.headers.cookie || '').split(';').map(x => x.trim()).find(x => x.startsWith('pizza_admin='))?.slice(12);
  if (!token) return false;
  const [value, signature] = token.split('.');
  const expected = createHmac('sha256', cookieSecret).update(value || '').digest('base64url');
  return safeEqual(signature || '', expected) && Date.now() - Number(value) < 12 * 60 * 60 * 1000;
};

async function notify(event, date, order = null) {
  if (!process.env.PIZZA_N8N_WEBHOOK_URL) return { delivered: false, reason: 'not-configured' };
  const day = store.day(date);
  const orders = Object.values(day.orders);
  const payload = { event, date, deadline: '10:30 Europe/Berlin', restaurant: catalog.restaurant, order: order ? { id: order.id, name: order.name, items: order.items, totalCents: total(order), total: money(total(order)) } : null };
  if (event === 'daily_summary') {
    const grandTotalCents = orders.reduce((sum, value) => sum + total(value), 0);
    const itemTotals = Object.values(orders.flatMap(value => value.items).reduce((map, line) => { const key = line.itemId; map[key] ||= { name: line.name, quantity: 0, totalCents: 0 }; map[key].quantity += line.quantity; map[key].totalCents += line.quantity * line.priceCents; return map; }, {}));
    payload.summary = { orders: orders.map(value => ({ name: value.name, items: value.items, totalCents: total(value), total: money(total(value)) })), itemTotals: itemTotals.map(item => ({ ...item, total: money(item.totalCents) })), grandTotalCents, grandTotal: money(grandTotalCents) };
  }
  const response = await fetch(process.env.PIZZA_N8N_WEBHOOK_URL, { method: 'POST', headers: { 'Content-Type': 'application/json', ...(process.env.PIZZA_N8N_WEBHOOK_SECRET ? { Authorization: `Bearer ${process.env.PIZZA_N8N_WEBHOOK_SECRET}` } : {}) }, body: JSON.stringify(payload), signal: AbortSignal.timeout(15_000) });
  if (!response.ok) throw new Error(`n8n returned ${response.status}`);
  return { delivered: true };
}

async function closeAndSummarize() {
  if (!afterDeadline()) return;
  const date = today(); const day = store.day(date); day.closed = true;
  if (!day.unlocked || day.summarySent) return store.save();
  try { await notify('daily_summary', date); day.summarySent = true; day.summaryError = null; }
  catch (error) { day.summaryError = error.message; console.error('Summary delivery failed:', error.message); }
  await store.save();
}
setInterval(() => closeAndSummarize().catch(console.error), 30_000).unref();
await closeAndSummarize();

createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://localhost');
    if (url.pathname === '/healthz') return json(res, 200, { ok: true });
    const ip = normalizeIp(req.headers['x-forwarded-for'] || req.socket.remoteAddress);
    const audience = classifyIp(ip, boschCidrs, ownerCidrs);
    if (!audience) {
      res.writeHead(404, { 'Cache-Control': 'no-store', ...noIndex });
      return res.end();
    }
    if (url.pathname === '/robots.txt') {
      res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'public, max-age=86400', ...noIndex });
      return res.end('User-agent: *\nDisallow: /\n');
    }
    const admin = isAdmin(req);
    if (url.pathname === '/api/state' && req.method === 'GET') {
      await closeAndSummarize(); const date = today(); const day = store.day(date);
      return json(res, 200, { date, audience, admin, restaurant: catalog.restaurant, restaurantWebsite: catalog.website, deadline: '10:30', open: day.unlocked && !day.closed && !afterDeadline(), items: catalog.items, orders: admin ? Object.values(day.orders).map(order => ({ ...order, tokenHash: undefined, totalCents: total(order) })) : undefined, summarySent: admin ? day.summarySent : undefined, summaryError: admin ? day.summaryError : undefined, paymentBase });
    }
    if (url.pathname === '/api/admin/login' && req.method === 'POST') {
      const input = await body(req); if (!adminPassword || !cookieSecret || !safeEqual(input.password, adminPassword)) return json(res, 401, { error: 'Falsches Passwort.' });
      return json(res, 200, { ok: true }, { 'Set-Cookie': `pizza_admin=${signedCookie()}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=43200` });
    }
    if (url.pathname === '/api/admin/session' && req.method === 'POST') {
      if (!admin) return json(res, 401, { error: 'Admin-Anmeldung erforderlich.' });
      const input = await body(req); const day = store.day(today());
      if (input.action === 'open' && !afterDeadline()) { day.unlocked = true; day.closed = false; }
      else if (input.action === 'close') day.closed = true;
      else if (input.action === 'retry-summary') { day.summarySent = false; await notify('daily_summary', today()); day.summarySent = true; day.summaryError = null; }
      else return json(res, 400, { error: 'Aktion ist jetzt nicht möglich.' });
      await store.save(); return json(res, 200, { ok: true });
    }
    if (url.pathname === '/api/orders' && req.method === 'POST') {
      await closeAndSummarize(); const input = await body(req); const date = today(); const day = store.day(date);
      if (!day.unlocked || day.closed || afterDeadline()) return json(res, 409, { error: 'Bestellungen sind geschlossen.' });
      const name = String(input.name || '').trim().slice(0, 80); if (!name) return json(res, 400, { error: 'Bitte Namen angeben.' });
      const selected = Array.isArray(input.items) ? input.items : [];
      const items = selected.map(line => { const item = catalog.items.find(value => value.id === line.itemId); const quantity = Number(line.quantity); return item && Number.isInteger(quantity) && quantity > 0 && quantity <= 20 ? { itemId: item.id, name: item.name, priceCents: item.priceCents, quantity } : null; }).filter(Boolean);
      if (!items.length) return json(res, 400, { error: 'Bitte mindestens einen Artikel wählen.' });
      const existing = input.id ? day.orders[input.id] : null;
      if (existing && !safeEqual(existing.tokenHash, hashToken(input.token || ''))) return json(res, 403, { error: 'Diese Bestellung gehört zu einem anderen Browser.' });
      const token = existing ? input.token : randomBytes(24).toString('base64url'); const id = existing?.id || randomBytes(10).toString('base64url');
      const order = { id, tokenHash: hashToken(token), name, items, createdAt: existing?.createdAt || new Date().toISOString(), updatedAt: new Date().toISOString() }; day.orders[id] = order; await store.save();
      try { await notify(existing ? 'order_updated' : 'order_created', date, order); } catch (error) { console.error('Order notification failed:', error.message); return json(res, 202, { id, token, totalCents: total(order), warning: 'Bestellung gespeichert, Telegram-Benachrichtigung fehlgeschlagen.' }); }
      return json(res, 200, { id, token, totalCents: total(order) });
    }
    const orderMatch = url.pathname.match(/^\/api\/orders\/([^/]+)$/);
    if (orderMatch && req.method === 'DELETE') {
      const input = await body(req); const day = store.day(today()); const order = day.orders[orderMatch[1]];
      if (!order || !safeEqual(order.tokenHash, hashToken(input.token || ''))) return json(res, 404, { error: 'Bestellung nicht gefunden.' });
      if (day.closed || afterDeadline()) return json(res, 409, { error: 'Bestellungen sind geschlossen.' });
      delete day.orders[order.id]; await store.save();
      try { await notify('order_cancelled', today(), order); } catch (error) { console.error('Cancellation notification failed:', error.message); }
      return json(res, 200, { ok: true });
    }
    if (files.has(url.pathname) && req.method === 'GET') { res.writeHead(200, { 'Content-Type': types[url.pathname], 'Cache-Control': 'no-cache', ...noIndex }); return res.end(files.get(url.pathname)); }
    return json(res, 404, { error: 'Nicht gefunden.' });
  } catch (error) { console.error(error); return json(res, 500, { error: 'Der Pizzaofen hat gerade ein technisches Problem.' }); }
}).listen(3000, '0.0.0.0', () => console.log('Pizza orders listening on :3000'));
