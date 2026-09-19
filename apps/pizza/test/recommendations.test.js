import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { loadCatalog } from '../src/catalog.js';
import { priceOrder } from '../src/orders.js';
import { buildRecommendations, cheaperAlternative, recommendOrder } from '../public/recommendations.js';

const catalog = await loadCatalog(new URL('../config/menu.json', import.meta.url));
const mapping = JSON.parse(await readFile(new URL('../config/pizza-equivalences.json', import.meta.url), 'utf8'));
const connections = buildRecommendations(catalog.items, mapping);
const line = (name, extraIds = [], quantity = 1) => ({ itemId: catalog.items.find(item => item.name === name).id, extraIds, quantity });

test('all configured recipes produce cheaper, server-valid replacements', () => {
  assert.equal(connections.length, mapping.connections.length);
  for (const connection of mapping.connections) {
    const original = line(connection.name);
    const alternative = cheaperAlternative(original, catalog.items, connections);
    assert.ok(alternative?.savingCents > 0, connection.name);
    assert.equal(priceOrder([alternative.line], catalog)[0].priceCents, alternative.priceCents);
  }
  assert.equal(cheaperAlternative(line('Pizza Funghi'), catalog.items, connections).savingCents, 104);
});

test('acceptance replaces the configuration and preserves extra toppings, dough and quantity', () => {
  const original = line('Pizza Salami', ['vollkornteig', 'ananas'], 2);
  const result = recommendOrder([original], catalog.items, connections, () => true);
  assert.deepEqual(result[0], line('Pizza Margherita', ['salami', 'vollkornteig', 'ananas'], 2));
  assert.equal(priceOrder(result, catalog)[0].priceCents, 1286);
});

test('declining preserves original lines; identical combinations prompt once', () => {
  const lines = [line('Pizza Funghi'), line('Pizza Funghi')];
  let prompts = 0;
  assert.deepEqual(recommendOrder(lines, catalog.items, connections, () => { prompts++; return false; }), lines);
  assert.equal(prompts, 1);
});

test('does not claim equivalence for uncertain recipes or discard double toppings', () => {
  assert.equal(cheaperAlternative(line('Pizza Vegetariana'), catalog.items, connections), null);
  assert.equal(cheaperAlternative(line('Pizza Salami', ['salami']), catalog.items, connections), null);
});

test('recalculates current prices and skips equal or more expensive replacements', () => {
  for (const priceCents of [1040, 2000]) {
    const items = catalog.items.map(item => item.name === 'Pizza Margherita' ? { ...item, priceCents } : item);
    assert.equal(cheaperAlternative(line('Pizza Funghi'), items, connections), null);
  }
});

test('changed recipes or missing toppings disable their connections', () => {
  const changed = catalog.items.map(item => item.name === 'Pizza Funghi' ? { ...item, description: 'different recipe' } : item);
  assert.equal(buildRecommendations(changed, mapping).length, mapping.connections.length - 1);
  const missing = catalog.items.map(item => ({ ...item, extras: [] }));
  assert.deepEqual(buildRecommendations(missing, mapping), []);
});

test('does not exceed the 20-pizza limit or partially replace an identical combination', () => {
  const lines = [line('Pizza Margherita', [], 19), line('Pizza Funghi'), line('Pizza Funghi')];
  assert.deepEqual(recommendOrder(lines, catalog.items, connections, () => assert.fail('must not prompt')), lines);
});
