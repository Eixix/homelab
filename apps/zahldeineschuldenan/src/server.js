import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { randomBytes } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import QRCode from 'qrcode';
import { parseAmount } from './amount.js';
import { createEpcPayload } from './epc.js';

const publicDir = fileURLToPath(new URL('../public/', import.meta.url));
const index = await readFile(`${publicDir}/index.html`, 'utf8');
const assetTypes = {
  'style.css': 'text/css; charset=utf-8',
  'app.js': 'text/javascript; charset=utf-8',
  'social-preview.jpg': 'image/jpeg',
};
const assets = new Map(await Promise.all(Object.entries(assetTypes).map(async ([name, type]) => [
  `/${name}`,
  { body: await readFile(`${publicDir}/${name}`), type },
])));

const send = (res, status, type, body, cache = 'no-store') => {
  res.writeHead(status, {
    'Content-Type': type,
    'Cache-Control': cache,
    'X-Content-Type-Options': 'nosniff',
    'X-Robots-Tag': 'noindex, nofollow, noarchive, nosnippet',
  });
  res.end(body);
};

const redirect = (res, location) => {
  res.writeHead(303, {
    Location: location,
    'Cache-Control': 'no-store',
    'X-Robots-Tag': 'noindex, nofollow, noarchive, nosnippet',
  });
  res.end();
};

const obfuscate = (value) => {
  const plain = Buffer.from(value, 'utf8');
  const key = randomBytes(plain.length);
  const masked = Buffer.allocUnsafe(plain.length);
  for (let index = 0; index < plain.length; index += 1) {
    masked[index] = plain[index] ^ key[index];
  }
  return {
    masked: masked.toString('base64'),
    key: key.toString('base64'),
  };
};

const escapeHtml = (value) => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('"', '&quot;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;');

const requestOrigin = (req) => {
  if (process.env.ZAHLDEINESCHULDENAN_HOST) {
    return `https://${process.env.ZAHLDEINESCHULDENAN_HOST}`;
  }
  const forwardedHost = req.headers['x-forwarded-host'];
  const host = String(forwardedHost || req.headers.host || 'localhost:3000').split(',')[0].trim();
  const forwardedProto = String(req.headers['x-forwarded-proto'] || 'http').split(',')[0].trim();
  return `${forwardedProto === 'https' ? 'https' : 'http'}://${host}`;
};

const renderPage = (req, data, amount = null) => {
  const origin = requestOrigin(req);
  const canonicalUrl = amount
    ? `${origin}/${encodeURIComponent(amount.canonical.replace('.', ','))}/`
    : `${origin}/`;
  const title = amount
    ? `Tobias fordert ${amount.display} ein 💸`
    : 'Zahl deine Schulden an Tobias! 💸';
  const description = amount
    ? `${amount.display} sind noch offen. Die freundliche Geldeintreibungsstelle akzeptiert PayPal und Überweisung.`
    : 'Die freundliche Geldeintreibungsstelle – jetzt offenen Betrag eingeben und bequem bezahlen.';
  const imageUrl = `${origin}/social-preview.jpg`;
  const meta = [
    ['property', 'og:type', 'website'],
    ['property', 'og:locale', 'de_DE'],
    ['property', 'og:site_name', 'Zahl deine Schulden an Tobias'],
    ['property', 'og:title', title],
    ['property', 'og:description', description],
    ['property', 'og:url', canonicalUrl],
    ['property', 'og:image', imageUrl],
    ['property', 'og:image:secure_url', imageUrl],
    ['property', 'og:image:type', 'image/jpeg'],
    ['property', 'og:image:width', '1200'],
    ['property', 'og:image:height', '630'],
    ['property', 'og:image:alt', 'Eine freche Euro-Münze erinnert ans Schuldenbezahlen.'],
    ['name', 'twitter:card', 'summary_large_image'],
    ['name', 'twitter:title', title],
    ['name', 'twitter:description', description],
    ['name', 'twitter:image', imageUrl],
  ].map(([attribute, name, content]) => `<meta ${attribute}="${name}" content="${escapeHtml(content)}">`).join('\n        ');

  return index
    .replace('__SOCIAL_META__', meta)
    .replace('__PAYMENT_DATA__', data ? JSON.stringify(data).replaceAll('<', '\\u003c') : 'null');
};

createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost');
  if (url.pathname === '/healthz') return send(res, 200, 'text/plain', 'ok');
  if (url.pathname === '/robots.txt') {
    return send(res, 200, 'text/plain; charset=utf-8', 'User-agent: *\nAllow: /\n');
  }

  if (assets.has(url.pathname)) {
    const asset = assets.get(url.pathname);
    const cache = url.pathname === '/social-preview.jpg' ? 'public, max-age=86400' : 'no-cache';
    return send(res, 200, asset.type, asset.body, cache);
  }

  if (url.pathname === '/' && url.searchParams.has('amount')) {
    const submittedAmount = parseAmount(url.searchParams.get('amount'));
    if (submittedAmount) {
      return redirect(res, `/${submittedAmount.canonical.replace('.', ',')}/`);
    }
  }

  const match = url.pathname.match(/^\/([^/]+)\/?$/);
  const amount = parseAmount(match?.[1]);
  if (!amount) return send(res, 404, 'text/html; charset=utf-8', renderPage(req, null));

  try {
    const payload = createEpcPayload({
      name: process.env.PAYMENT_RECIPIENT_NAME,
      iban: process.env.PAYMENT_IBAN,
      bic: process.env.PAYMENT_BIC,
      amount,
    });
    const qr = await QRCode.toDataURL(payload, { errorCorrectionLevel: 'M', margin: 2, width: 420 });
    const iban = process.env.PAYMENT_IBAN.replace(/\s/g, '').toUpperCase();
    const data = {
      amount,
      paypalUrl: `https://paypal.me/${encodeURIComponent(process.env.PAYPAL_ME_NAME || '')}/${amount.canonical}EUR`,
      bankTransfer: {
        recipient: process.env.PAYMENT_RECIPIENT_NAME,
        ibanObfuscated: obfuscate(iban),
        bic: (process.env.PAYMENT_BIC || '').replace(/\s/g, '').toUpperCase(),
        reference: 'Schulden begleichen',
      },
      qr,
    };
    return send(res, 200, 'text/html; charset=utf-8', renderPage(req, data, amount));
  } catch (error) {
    console.error(error.message);
    return send(res, 500, 'text/plain; charset=utf-8', 'Payment configuration is incomplete.');
  }
}).listen(3000, '0.0.0.0', () => console.log('Payment page listening on :3000'));
