import { isIP } from 'node:net';

export const DEFAULT_BOSCH_CIDRS = '139.15.0.0/16 185.112.176.0/22 192.48.31.0/24 193.108.217.0/24 193.141.57.0/24 194.39.218.0/23 2a03:cc00::/32';

export function normalizeIp(value = '') {
  const first = String(value).split(',')[0].trim();
  if (first.startsWith('::ffff:')) return first.slice(7);
  return first.replace(/^\[|\]$/g, '');
}

const ipv4Number = ip => ip.split('.').reduce((number, octet) => (number << 8n) + BigInt(octet), 0n);

const ipv6Number = (ip) => {
  const [left = '', right = ''] = ip.split('::');
  const before = left ? left.split(':') : [];
  const after = right ? right.split(':') : [];
  const groups = [...before, ...Array(Math.max(0, 8 - before.length - after.length)).fill('0'), ...after];
  if (groups.length !== 8) throw new Error('Invalid IPv6 address');
  return groups.reduce((number, group) => (number << 16n) + BigInt(`0x${group || '0'}`), 0n);
};

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

export const parseCidrs = (value = '') => String(value).split(/[\s,]+/).filter(Boolean);
export const isBoschIp = (ip, cidrs) => cidrs.some(cidr => ipInCidr(ip, cidr));
