import test from 'node:test';
import assert from 'node:assert/strict';
import { classifyIp, ipInCidr, normalizeIp } from '../src/network.js';

test('matches IPv4 and IPv6 CIDRs', () => {
  assert.equal(ipInCidr('139.15.12.3', '139.15.0.0/16'), true);
  assert.equal(ipInCidr('139.16.0.1', '139.15.0.0/16'), false);
  assert.equal(ipInCidr('2a03:cc00:fc1::2', '2a03:cc00::/32'), true);
});

test('normalizes forwarded addresses and classifies audiences', () => {
  assert.equal(normalizeIp('::ffff:10.0.0.2'), '10.0.0.2');
  assert.equal(classifyIp('139.15.4.2', ['139.15.0.0/16'], ['1.2.3.4/32']), 'bosch');
});
