const button = document.querySelector('#push-toggle');
const status = document.querySelector('#push-status');
const keyBytes = value => Uint8Array.from(atob(value.replace(/-/g, '+').replace(/_/g, '/')), char => char.charCodeAt(0));
async function saveSubscription(subscription, method = 'POST') {
  const response = await fetch('/api/push/subscription', {
    method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(subscription),
  });
  if (!response.ok) throw new Error('Push-Einstellung konnte nicht gespeichert werden. Bitte erneut versuchen.');
}

export async function initPush(publicKey) {
  if (!publicKey) { status.textContent = 'Benachrichtigungen sind noch nicht eingerichtet.'; return; }
  if (!window.isSecureContext || !('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) {
    status.textContent = 'Dieser Browser unterstützt hier kein Push. Auf iPhone/iPad: zum Home-Bildschirm hinzufügen und dort öffnen.';
    return;
  }
  let registration;
  let subscription;
  let synced = false;
  const render = () => {
    button.hidden = false;
    button.disabled = Notification.permission === 'denied' && !subscription;
    button.textContent = subscription && synced ? 'Benachrichtigungen ausschalten' : 'Benachrichtigungen einschalten';
    status.textContent = Notification.permission === 'denied'
      ? 'Benachrichtigungen sind im Browser blockiert. Du kannst sie in den Website-Einstellungen erlauben.'
      : subscription && synced ? 'Aktiv: Bestellstart und Pizza-Ankunft, auch bei geschlossener Seite.'
        : 'Freiwillig: eine Nachricht beim Bestellstart und wenn die Pizza da ist.';
  };
  try {
    await navigator.serviceWorker.register('/sw.js');
    registration = await navigator.serviceWorker.ready;
    subscription = await registration.pushManager.getSubscription();
    if (subscription) {
      const currentKey = new Uint8Array(subscription.options.applicationServerKey || []);
      const expected = keyBytes(publicKey);
      if (currentKey.length !== expected.length || currentKey.some((value, index) => value !== expected[index])) {
        await subscription.unsubscribe(); subscription = null;
      } else { await saveSubscription(subscription); synced = true; }
    }
    render();
  } catch {
    status.textContent = 'Push konnte nicht verbunden werden. Seite neu laden, um es erneut zu versuchen.';
    return;
  }
  button.addEventListener('click', async () => {
    button.disabled = true;
    try {
      if (subscription && synced) {
        await saveSubscription(subscription, 'DELETE');
        if (!await subscription.unsubscribe()) throw new Error('Bitte Benachrichtigungen in den Website-Einstellungen ausschalten.');
        subscription = null; synced = false;
      } else {
        // Ask only from this explicit click, including on iOS Home Screen apps.
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') { render(); return; }
        subscription ||= await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(publicKey) });
        await saveSubscription(subscription); synced = true;
      }
      render();
    } catch (error) {
      render();
      status.textContent = error.message || 'Push konnte nicht aktiviert werden. Bitte erneut versuchen.';
    } finally { button.disabled = Notification.permission === 'denied' && !subscription; }
  });
}
