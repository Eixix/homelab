// No fetch handler: never cache private pages or bypass the network allowlist.
self.addEventListener('push', event => {
  let message;
  try { message = event.data?.json(); } catch { /* Use a visible fallback. */ }
  event.waitUntil(self.registration.showNotification(message?.title || 'Pizza-Fernschreiber', {
    body: message?.body || 'Es gibt Neuigkeiten zur Pizza. Öffne die Seite für den aktuellen Stand.',
    tag: message?.tag || 'pizza-update',
    icon: '/pizza-icon.svg',
  }));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    const page = windows.find(client => new URL(client.url).pathname === '/');
    if (page) { await page.focus(); page.postMessage({ type: 'pizza-refresh' }); }
    else await self.clients.openWindow('/');
  })());
});
