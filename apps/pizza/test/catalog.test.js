import test from 'node:test';
import assert from 'node:assert/strict';
import { parseCatalog } from '../src/catalog.js';

test('parses the documented pipe catalog', () => {
  const catalog = parseCatalog('@restaurant=Pizzeria\n@website=https://example.test\nPizza | Margherita | 8,50 | Käse');
  assert.equal(catalog.restaurant, 'Pizzeria');
  assert.deepEqual(catalog.items[0], { id: 'item-1', category: 'Pizza', name: 'Margherita', description: 'Käse', priceCents: 850 });
});

test('rejects malformed prices', () => assert.throws(() => parseCatalog('Pizza | Test | gratis')));
