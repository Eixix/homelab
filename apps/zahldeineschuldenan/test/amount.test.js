import test from 'node:test';
import assert from 'node:assert/strict';
import { parseAmount } from '../src/amount.js';

test('accepts German and decimal URL amounts', () => {
  assert.equal(parseAmount('12,5').canonical, '12.50');
  assert.equal(parseAmount('12.50').cents, 1250);
  assert.equal(parseAmount('1').canonical, '1.00');
});

test('rejects unsafe or ambiguous amounts', () => {
  for (const value of ['', '0', '-2', '12.345', '1e3', '12 EUR', '1000000', '%E0%A4%A']) {
    assert.equal(parseAmount(value), null);
  }
});
