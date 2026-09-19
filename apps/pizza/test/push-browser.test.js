import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFile } from 'node:fs/promises';
const code = (await readFile(new URL('../public/push.js', import.meta.url), 'utf8')).replace('export async function initPush', 'async function initPush');

function browser({ permission = 'default', failSave = false } = {}) {
  const nodes = { '#push-toggle': { hidden: true, addEventListener: (_, handler) => { nodes.click = handler; } }, '#push-status': {} };
  const requests = []; let prompts = 0; let subscribed = 0; let unsubscribed = 0;
  const key = Buffer.alloc(65, 1).toString('base64url');
  const subscription = { endpoint: 'https://fcm.googleapis.com/test-only', keys: {}, unsubscribe: async () => { unsubscribed++; return true; } };
  const registration = { pushManager: {
    getSubscription: async () => null,
    subscribe: async options => { assert.equal(options.userVisibleOnly, true); subscribed++; return subscription; },
  } };
  const notification = { permission, requestPermission: async () => { prompts++; return notification.permission = 'granted'; } };
  const context = vm.createContext({
    Uint8Array, atob,
    document: { querySelector: selector => nodes[selector] },
    window: { isSecureContext: true, PushManager: {}, Notification: notification }, Notification: notification,
    navigator: { serviceWorker: { register: async path => { assert.equal(path, '/sw.js'); }, ready: Promise.resolve(registration) } },
    fetch: async (path, options) => { requests.push({ path, ...options }); return { ok: !failSave || requests.length > 1 }; },
  });
  vm.runInContext(code, context);
  return { nodes, requests, init: () => context.initPush(key), counts: () => ({ prompts, subscribed, unsubscribed }) };
}

test('permission is requested only by clicking opt-in; a second click unsubscribes', async () => {
  const page = browser(); await page.init();
  assert.equal(page.counts().prompts, 0);
  assert.equal(page.requests.length, 0);
  await page.nodes.click();
  assert.equal(page.counts().prompts, 1);
  assert.equal(page.requests[0].method, 'POST');
  assert.match(page.nodes['#push-status'].textContent, /Aktiv/);
  await page.nodes.click();
  assert.equal(page.requests[1].method, 'DELETE');
  assert.equal(page.counts().unsubscribed, 1);
  assert.match(page.nodes['#push-toggle'].textContent, /einschalten/);
});

test('blocked permissions are explained without prompting again', async () => {
  const page = browser({ permission: 'denied' }); await page.init();
  assert.equal(page.counts().prompts, 0);
  assert.equal(page.nodes['#push-toggle'].disabled, true);
  assert.match(page.nodes['#push-status'].textContent, /blockiert/);
});

test('server subscription failure is visible and can be retried without a second subscription', async () => {
  const page = browser({ failSave: true }); await page.init();
  await page.nodes.click();
  assert.match(page.nodes['#push-status'].textContent, /erneut versuchen/);
  assert.match(page.nodes['#push-toggle'].textContent, /einschalten/);
  await page.nodes.click();
  assert.equal(page.counts().subscribed, 1);
  assert.match(page.nodes['#push-status'].textContent, /Aktiv/);
});
