import test from 'node:test';
import assert from 'node:assert/strict';
import { createECDH, randomBytes } from 'node:crypto';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Store } from '../src/store.js';
import { PushService, validateSubscription } from '../src/push.js';

function subscription(endpoint = 'https://fcm.googleapis.com/fcm/send/test-only') {
  const key = createECDH('prime256v1'); key.generateKeys();
  return { endpoint, keys: { p256dh: key.getPublicKey().toString('base64url'), auth: randomBytes(16).toString('base64url') } };
}
async function fixture(t, send = async () => {}) {
  const path = await mkdtemp(join(tmpdir(), 'pizza-push-test-'));
  t.after(() => rm(path, { recursive: true, force: true }));
  const store = new Store(join(path, 'orders.json')); await store.load();
  const push = new PushService(store, 'https://pizza.example.com', send); await push.init();
  return { store, push };
}

test('keys and deduplicated subscriptions survive restart; unsubscribe requires matching keys', async t => {
  const { store, push } = await fixture(t);
  const sub = subscription(); await push.subscribe(sub); await push.subscribe(sub);
  assert.equal(Object.keys(store.data.push.subscriptions).length, 1);
  const restored = new Store(store.path); await restored.load();
  const restarted = new PushService(restored, 'https://pizza.example.com'); await restarted.init();
  assert.equal(restarted.publicKey, push.publicKey);
  await restarted.unsubscribe(subscription(sub.endpoint));
  assert.equal(Object.keys(restored.data.push.subscriptions).length, 1);
  await restarted.unsubscribe(sub);
  assert.equal(Object.keys(restored.data.push.subscriptions).length, 0);
});

test('rejects arbitrary destinations, deceptive provider names, and invalid encryption keys', () => {
  for (const endpoint of ['http://fcm.googleapis.com/a', 'https://127.0.0.1/a', 'https://example.com/a', 'https://fcm.googleapis.com.evil.example/a', 'https://fcm.googleapis.com:8443/a', 'https://user:pass@fcm.googleapis.com/a', 'https://fcm.googleapis.com/a#fragment']) {
    assert.throws(() => validateSubscription(subscription(endpoint)));
  }
  for (const keys of [{}, { p256dh: 'a'.repeat(87), auth: 'a'.repeat(22) }, { ...subscription().keys, auth: 'bad' }]) {
    assert.throws(() => validateSubscription({ ...subscription(), keys }));
  }
  for (const host of ['fcm.googleapis.com', 'updates.push.services.mozilla.com', 'web.push.apple.com', 'wns2.notify.windows.com']) {
    assert.equal(new URL(validateSubscription(subscription(`https://${host}/test-only`)).endpoint).hostname, host);
  }
});

test('broadcasts only once per event and day, with no order details and short expiry', async t => {
  const sent = [];
  const { push, store } = await fixture(t, async (...args) => { sent.push(args); });
  await push.subscribe(subscription());
  store.day('2026-09-19').orders.private = { name: 'Private customer' };
  await Promise.all([push.announce('open', '2026-09-19'), push.announce('open', '2026-09-19')]);
  await push.announce('arrived', '2026-09-19');
  await push.announce('close', '2026-09-19');
  await push.announce('open', '2026-09-20');
  assert.equal(sent.length, 3);
  assert.match(JSON.parse(sent[0][1]).body, /10:30/);
  assert.match(JSON.parse(sent[1][1]).body, /Pizza ist da/);
  for (const [, payload, options] of sent) {
    assert.ok(!payload.includes('Private customer'));
    assert.equal(options.TTL, 300);
    assert.equal(options.timeout, 5000);
    assert.equal(options.vapidDetails.publicKey, push.publicKey);
  }
  const restored = new Store(store.path); await restored.load();
  const restarted = new PushService(restored, 'https://pizza.example.com', async () => assert.fail('must not resend'));
  await restarted.init(); await restarted.announce('open', '2026-09-19');
});

test('expired subscriptions are pruned, transient failures retained and reported', async t => {
  const { store, push } = await fixture(t, async sub => {
    if (sub.endpoint.endsWith('/expired')) throw { statusCode: 410 };
    if (sub.endpoint.endsWith('/missing')) throw { statusCode: 404 };
    if (sub.endpoint.endsWith('/temporary')) throw { statusCode: 503 };
  });
  for (const name of ['expired', 'missing', 'temporary', 'working']) await push.subscribe(subscription(`https://fcm.googleapis.com/${name}`));
  await push.announce('arrived', '2026-09-19');
  assert.equal(Object.keys(store.data.push.subscriptions).length, 2);
  assert.deepEqual(store.day('2026-09-19').pushResult, { event: 'arrived', sent: 1, failed: 1, expired: 2, pending: false });
});

test('missing host disables push without generating runtime credentials', async t => {
  const { store } = await fixture(t);
  delete store.data.push;
  const push = new PushService(store, null, () => assert.fail('must not send'));
  await push.init(); await push.announce('open', '2026-09-19');
  assert.equal(push.publicKey, null);
  assert.equal(store.data.push, undefined);
});
