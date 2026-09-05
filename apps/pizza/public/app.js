import { createPizzaBoxScene } from './box-scene.js';
import { recommendOrder } from './recommendations.js';

const euro = cents => new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(cents / 100);
let saved = JSON.parse(localStorage.getItem('pizza-order') || 'null');
let state;
let boxScene;
const $ = selector => document.querySelector(selector);

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'Das hat nicht funktioniert.');
  return value;
}

const pizzaExtras = new Map();
function quantities() {
  return [...document.querySelectorAll('[data-item]')].flatMap(input => {
    const itemId = input.dataset.item;
    const quantity = Number(input.value);
    if (!(quantity > 0)) return [];
    const item = state.items.find(item => item.id === itemId);
    return item.extras?.length
      ? Array.from({ length: quantity }, (_, index) => ({ itemId, quantity: 1, extraIds: pizzaExtras.get(itemId)?.[index] || [] }))
      : [{ itemId, quantity }];
  });
}
function linePrice(line) {
  if (Number.isInteger(line.priceCents)) return line.priceCents;
  const item = state.items.find(item => item.id === line.itemId);
  return (item?.priceCents || 0) + (line.extraIds || []).reduce((sum, id) => sum + (item?.extras?.find(extra => extra.id === id)?.priceCents || 0), 0);
}
function renderExtras(input) {
  const item = state.items.find(item => item.id === input.dataset.item);
  if (!item.extras?.length) return;
  const container = input.closest('.menu-item').querySelector('.pizza-extras');
  const count = Math.max(0, Math.min(20, Math.floor(Number(input.value) || 0)));
  input.value = count;
  const selections = pizzaExtras.get(item.id) || [];
  while (selections.length < count) selections.push([]);
  selections.length = count;
  pizzaExtras.set(item.id, selections);
  container.innerHTML = selections.map((ids, index) => `<details class="extra-options"><summary>Pizza ${index + 1}: Extras wählen <b data-extra-price></b></summary><p>Aufpreise pro Pizza. Jede Auswahl gilt nur für diese Pizza.</p><div class="extra-grid">${item.extras.map(extra => `<label><input type="checkbox" data-extra="${escapeHtml(extra.id)}" data-pizza-index="${index}" ${ids.includes(extra.id) ? 'checked' : ''}><span>${escapeHtml(extra.name)}</span><b>+${euro(extra.priceCents)}</b></label>`).join('')}</div></details>`).join('');
  container.querySelectorAll('[data-extra]').forEach(checkbox => checkbox.addEventListener('change', () => {
    const index = Number(checkbox.dataset.pizzaIndex);
    const selected = new Set(selections[index]);
    if (checkbox.checked) selected.add(checkbox.dataset.extra); else selected.delete(checkbox.dataset.extra);
    selections[index] = [...selected];
    updateTotal();
  }));
}
function updateTotal() {
  const lines = quantities();
  const cents = lines.reduce((sum, line) => sum + line.quantity * linePrice(line), 0);
  $('#total').textContent = euro(cents);
  document.querySelectorAll('[data-item]').forEach(input => {
    const item = state.items.find(item => item.id === input.dataset.item);
    input.closest('.menu-item').querySelectorAll('[data-extra-price]').forEach((label, index) => {
      label.textContent = euro(linePrice({ itemId: item.id, extraIds: pizzaExtras.get(item.id)?.[index] || [] }));
    });
  });
}
function syncItem(input) {
  renderExtras(input);
  const row = input.closest('.menu-item');
  const selected = Number(input.value) > 0;
  row.classList.toggle('selected', selected);
  row.querySelector('[data-select]').checked = selected;
  row.querySelector('.stepper').hidden = !selected;
}
function escapeHtml(value) { const node = document.createElement('span'); node.textContent = value; return node.innerHTML; }

const wait = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
function packedTotal(record) { return record.totalCents ?? record.items.reduce((sum, line) => sum + linePrice(line) * line.quantity, 0); }
function fillOrderNote(record) {
  $('#box-name').textContent = record.name;
  $('#box-summary').innerHTML = record.items.map(line => {
    const item = state.items.find(candidate => candidate.id === line.itemId);
    const extras = (line.extraIds || []).map(id => item?.extras?.find(extra => extra.id === id)?.name || id);
    const name = line.name || (item?.name || line.itemId) + (extras.length ? ` + ${extras.join(', ')}` : '');
    return `<li><span>${line.quantity}× ${escapeHtml(name)}</span><b>${euro(linePrice(line) * line.quantity)}</b></li>`;
  }).join('');
  $('#box-total').textContent = euro(packedTotal(record));
  $('#box-actions').hidden = !state.open;
  $('#box-deadline').textContent = state.open ? 'Bis 10:30 kannst du die Box noch einmal öffnen.' : 'Bestellschluss. Diese Box bleibt jetzt zu.';
  if (state.paymentBase) { $('#box-pay').href = `${state.paymentBase}/${(packedTotal(record) / 100).toFixed(2).replace('.', ',')}/?reference=${encodeURIComponent(`Pizza ${state.date} – ${record.name}`)}`; $('#box-pay').hidden = false; }
}
async function showPackedOrder(record, animate = true) {
  fillOrderNote(record); document.body.classList.add('box-mode'); $('#box-stage').hidden = false;
  $('#box-stage').className = `box-stage ${animate ? 'packing' : 'packed'}`;
  if (animate) { $('#box-stage').scrollIntoView({ behavior: 'smooth', block: 'center' }); await boxScene.close(); $('#box-stage').className = 'box-stage packed'; }
  else boxScene.packed();
}
async function playBoxIntro() {
  if (sessionStorage.getItem('pizza-box-opened')) return;
  sessionStorage.setItem('pizza-box-opened', 'true'); document.body.classList.add('box-intro-mode'); $('#box-stage').hidden = false; $('#box-stage').className = 'box-stage intro';
  await boxScene.intro(); $('#box-stage').hidden = true; $('#box-stage').className = 'box-stage'; document.body.classList.remove('box-intro-mode'); document.body.classList.add('menu-arrival');
  await wait(650); document.body.classList.remove('menu-arrival');
}

function startCountdown() {
  const label = $('#box-countdown');
  const deadline = new Date(`${state.date}T10:30:00+02:00`).getTime();
  const arrival = new Date(`${state.date}T12:00:00+02:00`).getTime();
  const format = milliseconds => { const seconds = Math.max(0, Math.ceil(milliseconds / 1000)); const hours = Math.floor(seconds / 3600); const minutes = Math.floor((seconds % 3600) / 60); const rest = seconds % 60; return [hours, minutes, rest].map(value => String(value).padStart(2, '0')).join(':'); };
  const update = () => {
    const now = Date.now();
    if (now < deadline) label.textContent = `SCHLIESST IN ${format(deadline - now)}`;
    else if (now < arrival) label.textContent = `🔒 PIZZA IN CA. ${format(arrival - now)}`;
    else label.textContent = '🔒 PIZZA MÜSSTE DA SEIN';
    boxScene?.setCountdown(label.textContent);
  };
  update(); setInterval(update, 1000);
}

async function load() {
  state = await api('/api/state');
  if (saved && saved.date !== state.date) {
    localStorage.removeItem('pizza-order');
    saved = null;
  }
  boxScene = createPizzaBoxScene($('#box-canvas'), state.items);
  startCountdown();
  $('#closed').hidden = state.open;
  $('#closed-copy').textContent = state.open ? '' : ' Tobias muss die Ausgabe erst öffnen – oder 10:30 ist bereits durch.';
  $('#order-form').hidden = !state.open;
  const groups = state.items.reduce((result, item) => { (result[item.category] ||= []).push(item); return result; }, {});
  $('#menu').innerHTML = Object.entries(groups).map(([category, items], groupIndex) => `<details class="menu-group"><summary><span>0${groupIndex + 1}</span><b>${escapeHtml(category)}</b><small>${items.length} Positionen</small><i aria-hidden="true">＋</i></summary><div class="menu-items">${items.map(item => `<div class="menu-item"><label class="pick"><input data-select type="checkbox"><i aria-hidden="true">✓</i><span><b>${escapeHtml(item.name)}</b><small>${escapeHtml(item.description)}</small></span></label><strong>${euro(item.priceCents)}</strong><div class="stepper" hidden><button type="button" data-step="-1" aria-label="Eine Portion weniger">−</button><input data-item="${item.id}" type="number" inputmode="numeric" min="0" max="20" value="0" aria-label="Anzahl ${escapeHtml(item.name)}"><button type="button" data-step="1" aria-label="Eine Portion mehr">+</button></div><div class="pizza-extras"></div></div>`).join('')}</div></details>`).join('');
  document.querySelectorAll('[data-select]').forEach(checkbox => checkbox.addEventListener('change', () => { const input = checkbox.closest('.menu-item').querySelector('[data-item]'); input.value = checkbox.checked ? Math.max(1, Number(input.value)) : 0; syncItem(input); updateTotal(); }));
  document.querySelectorAll('[data-step]').forEach(button => button.addEventListener('click', () => { const input = button.closest('.stepper').querySelector('[data-item]'); input.value = Math.max(0, Math.min(20, Number(input.value) + Number(button.dataset.step))); syncItem(input); updateTotal(); }));
  document.querySelectorAll('[data-item]').forEach(input => input.addEventListener('input', () => { syncItem(input); updateTotal(); }));
  if (saved?.date === state.date) {
    $('#name').value = saved.name || '';
    restoreSelection(saved.items || []);
    $('#cancel').hidden = false;
  }
  updateTotal();
  if (saved?.date === state.date) await showPackedOrder(saved, false);
  else if (state.open) await playBoxIntro();
}

function restoreSelection(lines) {
  const counts = new Map();
  pizzaExtras.clear();
  for (const line of lines) {
    counts.set(line.itemId, (counts.get(line.itemId) || 0) + line.quantity);
    const selections = pizzaExtras.get(line.itemId) || [];
    for (let index = 0; index < line.quantity; index++) selections.push([...(line.extraIds || [])]);
    pizzaExtras.set(line.itemId, selections);
  }
  document.querySelectorAll('[data-item]').forEach(input => {
    input.value = counts.get(input.dataset.item) || 0;
    syncItem(input);
  });
  updateTotal();
}

$('#order-form').addEventListener('submit', async event => {
  event.preventDefault(); $('#status').textContent = '';
  const items = recommendOrder(quantities(), state.items, state.recommendations || [], alternative => confirm(
    `${alternative.name} kostet ${euro(alternative.priceCents)} statt ${euro(alternative.originalPriceCents)} für ${alternative.originalName}.\n\nLaut Speisekarte gleicher Belag – du sparst ${euro(alternative.savingCents)} pro Pizza.\n\nAlle ausgewählten Pizzen dieser Kombination durch die günstigere Variante ersetzen?`
  ));
  restoreSelection(items);
  const payload = { id: saved?.date === state.date ? saved.id : undefined, token: saved?.date === state.date ? saved.token : undefined, name: $('#name').value, items };
  try {
    const result = await api('/api/orders', { method: 'POST', body: JSON.stringify(payload) });
    const record = { ...payload, items: result.items, id: result.id, token: result.token || payload.token, totalCents: result.totalCents, date: state.date }; localStorage.setItem('pizza-order', JSON.stringify(record)); saved = record;
    $('#cancel').hidden = false; await showPackedOrder(record); if (result.warning) $('#status').textContent = result.warning;
  } catch (error) { $('#status').textContent = error.message; }
});
async function cancelOrder() {
  const record = JSON.parse(localStorage.getItem('pizza-order') || 'null'); if (!record || !confirm('Bestellung wirklich stornieren?')) return;
  try { await api(`/api/orders/${encodeURIComponent(record.id)}`, { method: 'DELETE', body: JSON.stringify({ token: record.token }) }); localStorage.removeItem('pizza-order'); location.reload(); } catch (error) { $('#status').textContent = error.message; }
}
$('#cancel').addEventListener('click', cancelOrder);
document.querySelector('[data-cancel-order]').addEventListener('click', cancelOrder);
$('#edit-order').addEventListener('click', async () => { $('#box-stage').className = 'box-stage reopening'; await boxScene.open(); document.body.classList.remove('box-mode'); $('#box-stage').hidden = true; $('#box-stage').className = 'box-stage'; $('#order-form').scrollIntoView({ behavior: 'smooth' }); });
load().catch(error => { $('#closed').hidden = false; $('#closed-copy').textContent = error.message; });
