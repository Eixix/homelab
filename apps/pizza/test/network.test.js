import test from 'node:test';
import assert from 'node:assert/strict';
import { classifyIp, ipInCidr, normalizeIp, requestClientIp } from '../src/network.js';

test('matches IPv4 and IPv6 CIDRs', () => {
  assert.equal(ipInCidr('139.15.12.3', '139.15.0.0/16'), true);
  assert.equal(ipInCidr('139.16.0.1', '139.15.0.0/16'), false);
  assert.equal(ipInCidr('2a03:cc00:fc1::2', '2a03:cc00::/32'), true);
});

test('normalizes forwarded addresses and classifies audiences', () => {
  assert.equal(normalizeIp('::ffff:10.0.0.2'), '10.0.0.2');
  assert.equal(classifyIp('139.15.4.2', ['139.15.0.0/16'], ['1.2.3.4/32']), 'bosch');
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
