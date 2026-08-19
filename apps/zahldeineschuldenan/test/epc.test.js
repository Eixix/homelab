import test from 'node:test';
import assert from 'node:assert/strict';
import { createEpcPayload } from '../src/epc.js';

test('uses a caller-provided payment reference', () => {
  const payload = createEpcPayload({ name: 'Tobias', iban: 'DE89370400440532013000', amount: { canonical: '12.50' }, reference: 'Pizza 2026-08-19 – Ada' });
  assert.match(payload, /Pizza 2026-08-19 – Ada/);
});

test('strips line breaks from the reference', () => {
  const payload = createEpcPayload({ name: 'Tobias', iban: 'DE89370400440532013000', amount: { canonical: '12.50' }, reference: 'Pizza\nAda' });
  assert.match(payload, /Pizza Ada/);
});
