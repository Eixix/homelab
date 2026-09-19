import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
const code = await readFile(new URL('../public/sw.js', import.meta.url), 'utf8');
function worker(clients = {}) {
  const handlers = {}; const shown = [];
  vm.runInNewContext(code, { URL, self: {
    addEventListener: (event, handler) => { handlers[event] = handler; },
    registration: { showNotification: async (...args) => { shown.push(args); } }, clients,
  } });
  return { handlers, shown };
}

test('push displays a notification without any open page or network fetch', async () => {
  const { handlers, shown } = worker();
  let done;
  handlers.push({ data: { json: () => ({ title: 'Pizza', body: 'Pizza ist da!', tag: 'arrival' }) }, waitUntil: promise => { done = promise; } });
  await done;
  assert.equal(shown[0][1].body, 'Pizza ist da!');
  assert.equal(shown[0][1].tag, 'arrival');
  assert.equal(handlers.fetch, undefined);
});

test('click focuses and refreshes an existing page without discarding its draft', async () => {
  let focused = false; let refreshed = false; let closed = false; let done;
  const page = { url: 'https://pizza.example.com/', focus: async () => { focused = true; }, postMessage: message => { refreshed = message.type === 'pizza-refresh'; } };
  const { handlers } = worker({ matchAll: async () => [page], openWindow: () => assert.fail('must preserve existing page') });
  handlers.notificationclick({ notification: { close: () => { closed = true; } }, waitUntil: promise => { done = promise; } });
  await done;
  assert.ok(focused && refreshed && closed);
});

test('click opens the pizza homepage if no page is open', async () => {
  let opened; let done;
  const { handlers } = worker({ matchAll: async () => [], openWindow: async url => { opened = url; } });
  handlers.notificationclick({ notification: { close() {} }, waitUntil: promise => { done = promise; } });
  await done; assert.equal(opened, '/');
});
