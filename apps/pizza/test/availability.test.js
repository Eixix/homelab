import test from 'node:test';
import assert from 'node:assert/strict';
import { effectiveCatalog, validateDeal } from '../src/availability.js';
import { loadCatalog } from '../src/catalog.js';
import { priceOrder } from '../src/orders.js';
const catalog = await loadCatalog(new URL('../config/menu.json', import.meta.url));
const pizza = catalog.items.find(item => item.name === 'Pizza Margherita');

test('legacy settings keep the deal and disabled deal uses regular price including extras', () => {
  assert.equal(effectiveCatalog(catalog).items.find(item => item.id === pizza.id).priceCents, 936);
  const regular = effectiveCatalog(catalog, { dealEnabled: false });
  const [line] = priceOrder([{ itemId: pizza.id, quantity: 2, extraIds: ['funghi'] }], regular);
  assert.equal(line.priceCents, 1140);
  assert.equal(pizza.priceCents, 936);
  assert.deepEqual(regular.items.filter(item => item.id !== pizza.id), catalog.items.filter(item => item.id !== pizza.id));
});

test('switching the deal back on restores catalog price without repricing saved orders', () => {
  const settings = validateDeal({ dealEnabled: false, regularPriceCents: 1040 });
  const saved = priceOrder([{ itemId: pizza.id, quantity: 1 }], effectiveCatalog(catalog, settings));
  const restored = effectiveCatalog(catalog, { ...settings, dealEnabled: true });
  assert.equal(priceOrder([{ itemId: pizza.id, quantity: 1 }], restored)[0].priceCents, 936);
  assert.equal(saved[0].priceCents, 1040);
});

test('rejects invalid settings and prices', () => {
  for (const price of [undefined, null, '1040', 0, -1, 10.4, 100001]) {
    assert.throws(() => validateDeal({ dealEnabled: false, regularPriceCents: price }));
  }
  assert.throws(() => validateDeal({ dealEnabled: 'false', regularPriceCents: 1040 }));
});
