import { createHash, ECDH } from 'node:crypto';
import webpush from 'web-push';

const endpointId = endpoint => createHash('sha256').update(endpoint).digest('hex');
const providerAllowed = host => host === 'fcm.googleapis.com'
  || host === 'updates.push.services.mozilla.com'
  || host.endsWith('.push.services.mozilla.com')
  || host.endsWith('.push.apple.com')
  || host.endsWith('.notify.windows.com');

export function validateSubscription(input) {
  try {
    if (typeof input?.endpoint !== 'string' || input.endpoint.length > 4096) throw new Error();
    const url = new URL(input.endpoint);
    if (url.protocol !== 'https:' || url.port || url.username || url.password || url.hash || !providerAllowed(url.hostname)) throw new Error();
    const { p256dh, auth } = input.keys || {};
    if (typeof p256dh !== 'string' || typeof auth !== 'string' || !/^[A-Za-z0-9_-]{87}$/.test(p256dh) || !/^[A-Za-z0-9_-]{22}$/.test(auth)) throw new Error();
    ECDH.convertKey(Buffer.from(p256dh, 'base64url'), 'prime256v1');
    return { endpoint: url.href, keys: { p256dh, auth } };
  } catch { throw new Error('Ungültiges oder nicht unterstütztes Push-Abonnement.'); }
}

export class PushService {
  constructor(store, subject, send = webpush.sendNotification) {
    this.store = store;
    this.subject = subject;
    this.send = send;
  }

  async init() {
    if (!this.subject) return;
    if (!this.store.data.push) {
      this.store.data.push = { ...webpush.generateVAPIDKeys(), subscriptions: {} };
      await this.store.save();
    }
  }

  get publicKey() { return this.subject ? this.store.data.push.publicKey : null; }

  async subscribe(input) {
    const subscription = validateSubscription(input);
    const entries = this.store.data.push.subscriptions;
    const id = endpointId(subscription.endpoint);
    if (!entries[id] && Object.keys(entries).length >= 1000) throw new Error('Zu viele Push-Abonnements. Bitte Tobias kontaktieren.');
    entries[id] = subscription;
    await this.store.save();
  }

  async unsubscribe(input) {
    const subscription = validateSubscription(input);
    const entries = this.store.data.push.subscriptions;
    const id = endpointId(subscription.endpoint);
    // Knowing a public endpoint alone is insufficient to remove another device.
    if (entries[id]?.keys.auth === subscription.keys.auth && entries[id]?.keys.p256dh === subscription.keys.p256dh) {
      delete entries[id];
      await this.store.save();
    }
  }

  async announce(event, date) {
    const messages = {
      open: 'Bestellungen sind geöffnet! Bestelle deine Pizza bis 10:30.',
      arrived: 'Pizza ist da! Bereit zur Abholung.',
    };
    if (!this.publicKey || !messages[event]) return;
    const day = this.store.day(date);
    day.pushAnnounced ||= {};
    if (day.pushAnnounced[event]) return;
    day.pushAnnounced[event] = true;
    const entries = this.store.data.push.subscriptions;
    const queue = Object.entries(entries);
    const result = { event, sent: 0, failed: 0, expired: 0, pending: true };
    day.pushResult = result;
    await this.store.save();
    const payload = JSON.stringify({ title: 'Pizza-Fernschreiber', body: messages[event], tag: `pizza-${date}-${event}` });
    const { publicKey, privateKey } = this.store.data.push;
    await Promise.all(Array.from({ length: Math.min(8, queue.length) }, async () => {
      while (queue.length) {
        const [id, subscription] = queue.shift();
        try {
          await this.send(subscription, payload, {
            vapidDetails: { subject: this.subject, publicKey, privateKey },
            TTL: 300, timeout: 5000, urgency: 'high',
          });
          result.sent++;
        } catch (error) {
          if (error.statusCode === 404 || error.statusCode === 410) {
            if (entries[id] === subscription) delete entries[id];
            result.expired++;
          } else result.failed++;
        }
      }
    }));
    result.pending = false;
    await this.store.save();
  }
}
