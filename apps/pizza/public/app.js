const euro = cents => new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(cents / 100);
let saved = JSON.parse(localStorage.getItem('pizza-order') || 'null');
let state;
const $ = selector => document.querySelector(selector);

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'Das hat nicht funktioniert.');
  return value;
}

function quantities() {
  return [...document.querySelectorAll('[data-item]')].map(input => ({ itemId: input.dataset.item, quantity: Number(input.value) })).filter(line => line.quantity > 0);
}
function updateTotal() {
  const cents = quantities().reduce((sum, line) => sum + line.quantity * state.items.find(item => item.id === line.itemId).priceCents, 0);
  $('#total').textContent = euro(cents);
}
function syncItem(input) {
  const row = input.closest('.menu-item');
  const selected = Number(input.value) > 0;
  row.classList.toggle('selected', selected);
  row.querySelector('[data-select]').checked = selected;
  row.querySelector('.stepper').hidden = !selected;
}
function renderOrders() {
  $('#orders').innerHTML = state.orders?.length ? state.orders.map(order => `<article><b>${escapeHtml(order.name)}</b><span>${euro(order.totalCents)}</span><ul>${order.items.map(line => `<li>${line.quantity}× ${escapeHtml(line.name)}</li>`).join('')}</ul></article>`).join('') : '<p>Noch gähnende Leere.</p>';
}
function escapeHtml(value) { const node = document.createElement('span'); node.textContent = value; return node.innerHTML; }

async function load() {
  state = await api('/api/state');
  document.body.dataset.audience = state.audience;
  $('#closed').hidden = state.open;
  $('#closed-copy').textContent = state.open ? '' : ' Tobias muss die Ausgabe erst öffnen – oder 10:30 ist bereits durch.';
  $('#order-form').hidden = !state.open;
  const groups = state.items.reduce((result, item) => { (result[item.category] ||= []).push(item); return result; }, {});
  $('#menu').innerHTML = Object.entries(groups).map(([category, items], groupIndex) => `<section class="menu-group"><h2><span>0${groupIndex + 1}</span>${escapeHtml(category)}</h2>${items.map(item => `<div class="menu-item"><label class="pick"><input data-select type="checkbox"><i aria-hidden="true">✓</i><span><b>${escapeHtml(item.name)}</b><small>${escapeHtml(item.description)}</small></span></label><strong>${euro(item.priceCents)}</strong><div class="stepper" hidden><button type="button" data-step="-1" aria-label="Eine Portion weniger">−</button><input data-item="${item.id}" type="number" inputmode="numeric" min="0" max="20" value="0" aria-label="Anzahl ${escapeHtml(item.name)}"><button type="button" data-step="1" aria-label="Eine Portion mehr">+</button></div></div>`).join('')}</section>`).join('');
  document.querySelectorAll('[data-select]').forEach(checkbox => checkbox.addEventListener('change', () => { const input = checkbox.closest('.menu-item').querySelector('[data-item]'); input.value = checkbox.checked ? Math.max(1, Number(input.value)) : 0; syncItem(input); updateTotal(); }));
  document.querySelectorAll('[data-step]').forEach(button => button.addEventListener('click', () => { const input = button.closest('.stepper').querySelector('[data-item]'); input.value = Math.max(0, Math.min(20, Number(input.value) + Number(button.dataset.step))); syncItem(input); updateTotal(); }));
  document.querySelectorAll('[data-item]').forEach(input => input.addEventListener('input', () => { syncItem(input); updateTotal(); }));
  if (saved?.date === state.date) {
    $('#name').value = saved.name || '';
    saved.items?.forEach(line => { const input = document.querySelector(`[data-item="${CSS.escape(line.itemId)}"]`); if (input) { input.value = line.quantity; syncItem(input); } });
    $('#cancel').hidden = false;
  }
  updateTotal();
  $('#dashboard').hidden = !state.admin; $('#login').hidden = state.admin;
  if (state.admin) renderOrders();
}

$('#order-form').addEventListener('submit', async event => {
  event.preventDefault(); $('#status').textContent = '';
  const payload = { id: saved?.date === state.date ? saved.id : undefined, token: saved?.date === state.date ? saved.token : undefined, name: $('#name').value, items: quantities() };
  try {
    const result = await api('/api/orders', { method: 'POST', body: JSON.stringify(payload) });
    const record = { ...payload, id: result.id, token: result.token || payload.token, date: state.date }; localStorage.setItem('pizza-order', JSON.stringify(record)); saved = record;
    $('#success').hidden = false; $('#cancel').hidden = false;
    if (state.paymentBase) { $('#pay').href = `${state.paymentBase}/${(result.totalCents / 100).toFixed(2).replace('.', ',')}/?reference=${encodeURIComponent(`Pizza ${state.date} – ${payload.name}`)}`; $('#pay').hidden = false; }
    $('#success').scrollIntoView({ behavior: 'smooth' }); if (result.warning) $('#status').textContent = result.warning;
  } catch (error) { $('#status').textContent = error.message; }
});
$('#cancel').addEventListener('click', async () => {
  const record = JSON.parse(localStorage.getItem('pizza-order') || 'null'); if (!record || !confirm('Bestellung wirklich stornieren?')) return;
  try { await api(`/api/orders/${encodeURIComponent(record.id)}`, { method: 'DELETE', body: JSON.stringify({ token: record.token }) }); localStorage.removeItem('pizza-order'); location.reload(); } catch (error) { $('#status').textContent = error.message; }
});
$('#login').addEventListener('submit', async event => { event.preventDefault(); try { await api('/api/admin/login', { method: 'POST', body: JSON.stringify({ password: $('#password').value }) }); location.reload(); } catch (error) { alert(error.message); } });
document.querySelector('.admin-actions').addEventListener('click', async event => { const action = event.target.dataset.action; if (!action) return; try { await api('/api/admin/session', { method: 'POST', body: JSON.stringify({ action }) }); location.reload(); } catch (error) { alert(error.message); } });
load().catch(error => { $('#closed').hidden = false; $('#closed-copy').textContent = error.message; });
