import test from 'node:test';
import assert from 'node:assert/strict';
import { loadCatalog, parseCatalog } from '../src/catalog.js';
import { priceOrder, summarizeItems } from '../src/orders.js';

const catalog = await loadCatalog(new URL('../config/menu.json', import.meta.url));
const pizza = catalog.items.find(item => item.name === 'Pizza Margherita');
const order = (extraIds = [], quantity = 1) => ({ itemId: pizza.id, quantity, extraIds });

test('imports all 52 options and calculates Margherita plus Funghi from catalog prices', () => {
  assert.equal(pizza.extras.length, 52);
  const [line] = priceOrder([{ ...order(['funghi']), priceCents: 1 }], catalog);
  assert.equal(line.priceCents, 1036);
  assert.equal(line.name, 'Pizza Margherita + Funghi');
  assert.equal(line.extras[0].priceCents, 100);
  assert.ok(line.priceCents < catalog.items.find(item => item.name === 'Pizza Funghi').priceCents);
});

test('dough and multiple toppings are charged on every pizza and selections survive JSON persistence', () => {
  const items = priceOrder([order(['vollkornteig', 'salami'], 2)], catalog);
  assert.equal(items[0].priceCents * items[0].quantity, 2372);
  const restored = JSON.parse(JSON.stringify(items));
  assert.deepEqual(priceOrder(restored, catalog), items);
});

test('summary groups identical combinations and keeps different or plain pizzas separate', () => {
  const items = priceOrder([order(), order(['salami']), order(['funghi', 'vollkornteig']), order(['vollkornteig', 'funghi'])], catalog);
  const summary = summarizeItems([{ items }]);
  assert.equal(summary.length, 3);
  assert.equal(summary[2].quantity, 2);
  assert.equal(summary[2].totalCents, 2272);
});

test('old orders without extras remain supported', () => {
  const items = priceOrder([{ itemId: pizza.id, quantity: 2 }], catalog);
  assert.deepEqual(items, [{ itemId: pizza.id, name: pizza.name, priceCents: 936, quantity: 2 }]);
});

test('rejects unknown, repeated, malformed, and inapplicable extras', () => {
  for (const ids of [['free-cheese'], ['salami', 'salami'], 'salami', [null]]) {
    assert.throws(() => priceOrder([order(ids)], catalog));
  }
  const party = catalog.items.find(item => item.category === 'Party-Pizza');
  assert.throws(() => priceOrder([{ itemId: party.id, quantity: 1, extraIds: ['salami'] }], catalog));
});

test('rejects invalid lines and enforces the quantity limit across configurations', () => {
  for (const selected of [[], [null], [order([], 0)], [order([], 1.5)], [order([], 21)], [order([], 20), order(['salami'])]]) {
    assert.throws(() => priceOrder(selected, catalog));
  }
});

test('catalog rejects invalid extra prices and missing groups', () => {
  const item = { ...pizza, extraGroup: 'pizza' };
  assert.throws(() => parseCatalog(JSON.stringify({ items: [item] })));
  assert.throws(() => parseCatalog(JSON.stringify({ items: [item], extraGroups: { pizza: [{ id: 'x', name: 'X', priceCents: -1 }] } })));
});
