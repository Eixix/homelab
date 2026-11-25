import { isIP } from 'node:net';

export function normalizeIp(value = '') {
  const first = String(value).split(',')[0].trim();
  if (first.startsWith('::ffff:')) return first.slice(7);
  return first.replace(/^\[|\]$/g, '');
}

// Only use this behind the Cloudflare peer check in Traefik. X-Forwarded-For
// may contain values supplied by the visitor, or be rewritten by Anubis.
export function requestClientIp(req) {
  const value = req.headers['cf-connecting-ip'] ?? req.socket.remoteAddress ?? '';
  if (typeof value !== 'string' || !isIP(value.trim())) return '';
  return normalizeIp(value.trim());
}

function ipv4Number(ip) {
  return ip.split('.').reduce((number, octet) => (number << 8n) + BigInt(octet), 0n);
}

function ipv6Number(ip) {
  const [left = '', right = ''] = ip.split('::');
  const expand = part => part ? part.split(':') : [];
  const before = expand(left);
  const after = expand(right);
  const groups = [...before, ...Array(Math.max(0, 8 - before.length - after.length)).fill('0'), ...after];
  if (groups.length !== 8) throw new Error('Invalid IPv6 address');
  return groups.reduce((number, group) => (number << 16n) + BigInt(`0x${group || '0'}`), 0n);
}

export function ipInCidr(ip, cidr) {
  const [network, bitsText] = cidr.trim().split('/');
  const version = isIP(ip);
  if (!version || version !== isIP(network)) return false;
  const width = version === 4 ? 32 : 128;
  const bits = bitsText === undefined ? width : Number(bitsText);
  if (!Number.isInteger(bits) || bits < 0 || bits > width) return false;
  const parse = version === 4 ? ipv4Number : ipv6Number;
  const shift = BigInt(width - bits);
  return (parse(ip) >> shift) === (parse(network) >> shift);
}

export function parseCidrs(value = '') {
  return String(value).split(/[\s,]+/).map(item => item.trim()).filter(Boolean);
}

export function classifyIp(ip, boschCidrs, ownerCidrs) {
  if (boschCidrs.some(cidr => ipInCidr(ip, cidr))) return 'bosch';
  if (ownerCidrs.some(cidr => ipInCidr(ip, cidr))) return 'owner';
  return null;
}
