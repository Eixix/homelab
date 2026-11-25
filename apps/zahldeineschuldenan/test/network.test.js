import test from 'node:test';
import assert from 'node:assert/strict';
import { isBoschIp, normalizeIp, requestClientIp, parseCidrs } from '../src/network.js';

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

test('uses the verified Cloudflare visitor IP instead of a forged forwarding chain', () => {
  const req = {
    headers: { 'cf-connecting-ip': '203.0.113.4', 'x-forwarded-for': '139.15.2.3, 173.245.48.1' },
    socket: { remoteAddress: '172.18.0.1' },
  };
  assert.equal(requestClientIp(req), '203.0.113.4');
  req.headers['cf-connecting-ip'] = '139.15.2.3';
  assert.equal(requestClientIp(req), '139.15.2.3');
  req.headers['cf-connecting-ip'] = '2a03:cc00::1234';
  assert.equal(requestClientIp(req), '2a03:cc00::1234');
  req.headers['cf-connecting-ip'] = '139.15.2.3, 203.0.113.4';
  assert.equal(requestClientIp(req), '');
  delete req.headers['cf-connecting-ip'];
  assert.equal(requestClientIp(req), '172.18.0.1');
});
