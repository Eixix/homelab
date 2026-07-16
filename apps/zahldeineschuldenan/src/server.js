import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { fileURLToPath } from 'node:url';
import QRCode from 'qrcode';
import { parseAmount } from './amount.js';
import { createEpcPayload } from './epc.js';

const publicDir = fileURLToPath(new URL('../public/', import.meta.url));
const index = await readFile(`${publicDir}/index.html`, 'utf8');
const assets = new Map(await Promise.all(['style.css', 'app.js'].map(async (name) => [
  `/${name}`,
  await readFile(`${publicDir}/${name}`),
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

createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost');
  if (url.pathname === '/healthz') return send(res, 200, 'text/plain', 'ok');
  if (url.pathname === '/robots.txt') {
    return send(res, 200, 'text/plain; charset=utf-8', 'User-agent: *\nDisallow: /\n');
  }

  if (assets.has(url.pathname)) {
    const type = url.pathname.endsWith('.css') ? 'text/css; charset=utf-8' : 'text/javascript; charset=utf-8';
    return send(res, 200, type, assets.get(url.pathname), 'public, max-age=3600');
  }

  const match = url.pathname.match(/^\/([^/]+)\/?$/);
  const amount = parseAmount(match?.[1]);
  if (!amount) return send(res, 404, 'text/html; charset=utf-8', index.replace('__PAYMENT_DATA__', 'null'));

  try {
    const payload = createEpcPayload({
      name: process.env.PAYMENT_RECIPIENT_NAME,
      iban: process.env.PAYMENT_IBAN,
      bic: process.env.PAYMENT_BIC,
      amount,
    });
    const qr = await QRCode.toDataURL(payload, { errorCorrectionLevel: 'M', margin: 2, width: 420 });
    const data = {
      amount,
      paypalUrl: `https://paypal.me/${encodeURIComponent(process.env.PAYPAL_ME_NAME || '')}/${amount.canonical}EUR`,
      bankTransfer: {
        recipient: process.env.PAYMENT_RECIPIENT_NAME,
        iban: process.env.PAYMENT_IBAN.replace(/\s/g, '').toUpperCase(),
        bic: (process.env.PAYMENT_BIC || '').replace(/\s/g, '').toUpperCase(),
        reference: 'Schulden begleichen',
      },
      qr,
    };
    return send(res, 200, 'text/html; charset=utf-8', index.replace('__PAYMENT_DATA__', JSON.stringify(data).replaceAll('<', '\\u003c')));
  } catch (error) {
    console.error(error.message);
    return send(res, 500, 'text/plain; charset=utf-8', 'Payment configuration is incomplete.');
  }
}).listen(3000, '0.0.0.0', () => console.log('Payment page listening on :3000'));
