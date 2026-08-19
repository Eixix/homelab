import test from 'node:test';
import assert from 'node:assert/strict';
import { isBoschIp, normalizeIp, parseCidrs } from '../src/network.js';

test('uses the first forwarded client address', () => {
  assert.equal(normalizeIp('139.15.2.3, 172.18.0.1'), '139.15.2.3');
  assert.equal(normalizeIp('::ffff:192.48.31.4'), '192.48.31.4');
});

test('matches Bosch IPv4 and IPv6 ranges', () => {
  const cidrs = parseCidrs('139.15.0.0/16, 2a03:cc00::/32');
  assert.equal(isBoschIp('139.15.42.7', cidrs), true);
  assert.equal(isBoschIp('2a03:cc00::1234', cidrs), true);
  assert.equal(isBoschIp('203.0.113.4', cidrs), false);
});
