const $ = selector => document.querySelector(selector);
const euro = cents => new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(cents / 100);
const escapeHtml = value => { const node = document.createElement('span'); node.textContent = value; return node.innerHTML; };

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'Das hat nicht funktioniert.');
  return value;
}

function render(state) {
  $('#login').hidden = state.admin;
  $('#dashboard').hidden = !state.admin;
  if (!state.admin) return;
  $('#day-state').textContent = state.open ? `Geöffnet bis ${state.deadline}` : 'Bestellungen geschlossen';
  if (!dealDirty) {
    $('#deal-enabled').checked = state.deal.dealEnabled !== false;
    $('#regular-price').value = state.deal.regularPriceCents ? (state.deal.regularPriceCents / 100).toFixed(2) : '';
  }
  $('#day-state').textContent += state.arrived ? ' · Pizza ist da!' : '';
  const delivery = state.pushResult;
  $('#push-delivery').textContent = delivery ? `Push (${delivery.event === 'open' ? 'Bestellstart' : 'Ankunft'}): ${delivery.pending ? 'wird versendet · ' : ''}${delivery.sent} angenommen, ${delivery.failed} fehlgeschlagen, ${delivery.expired} abgelaufen.` : '';
  $('#orders').innerHTML = state.orders?.length ? state.orders.map(order => `<article><b>${escapeHtml(order.name)}</b><span>${euro(order.totalCents)}</span><button class="delete-order" data-delete-order="${escapeHtml(order.id)}" data-order-name="${escapeHtml(order.name)}">Löschen</button><ul>${order.items.map(line => `<li>${line.quantity}× ${escapeHtml(line.name)}</li>`).join('')}</ul></article>`).join('') : '<p>Noch gähnende Leere.</p>';
}

async function load() { render(await api('/api/state')); }
$('#login').addEventListener('submit', async event => { event.preventDefault(); $('#login-error').textContent = ''; try { await api('/api/admin/login', { method: 'POST', body: JSON.stringify({ password: $('#password').value }) }); await load(); } catch (error) { $('#login-error').textContent = error.message; } });
$('.admin-actions').addEventListener('click', async event => { const action = event.target.dataset.action; if (!action) return; if (action === 'clear-orders' && !confirm('Wirklich alle heutigen Bestellungen unwiderruflich löschen?')) return; try { const result = await api('/api/admin/session', { method: 'POST', body: JSON.stringify({ action }) }); await load(); if (action === 'open') alert('Bestellungen sind jetzt geöffnet.'); if (action === 'clear-orders') alert(`${result.deleted} Bestellungen wurden gelöscht.`); } catch (error) { alert(action === 'open' ? `Öffnen fehlgeschlagen: ${error.message}` : error.message); } });
$('#orders').addEventListener('click', async event => { const button = event.target.closest('[data-delete-order]'); if (!button) return; if (!confirm(`Bestellung von ${button.dataset.orderName} wirklich löschen?`)) return; try { await api(`/api/admin/orders/${encodeURIComponent(button.dataset.deleteOrder)}`, { method: 'DELETE' }); await load(); } catch (error) { alert(error.message); } });
load().catch(error => { $('#login-error').textContent = error.message; });

let dealDirty = false;
$('#deal-form').addEventListener('input', () => { dealDirty = true; });
$('#deal-form').addEventListener('submit', async event => {
  event.preventDefault();
  try {
    await api('/api/admin/deal', { method: 'POST', body: JSON.stringify({ dealEnabled: $('#deal-enabled').checked, regularPriceCents: Math.round(Number($('#regular-price').value) * 100) }) });
    dealDirty = false; $('#deal-status').textContent = 'Gespeichert.'; await load();
  } catch (error) { $('#deal-status').textContent = error.message; }
});
setInterval(() => load().catch(() => {}), 15000);
document.addEventListener('visibilitychange', () => { if (!document.hidden) load().catch(() => {}); });
