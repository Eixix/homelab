const MAX_CENTS = 999_999_99;

export function parseAmount(segment) {
  if (!segment) return null;

  let decoded;
  try {
    decoded = decodeURIComponent(segment).trim().replace(',', '.');
  } catch {
    return null;
  }
  if (!/^\d+(?:\.\d{1,2})?$/.test(decoded)) return null;

  const [euros, decimals = ''] = decoded.split('.');
  const cents = Number(euros) * 100 + Number(decimals.padEnd(2, '0'));
  if (!Number.isSafeInteger(cents) || cents < 1 || cents > MAX_CENTS) return null;

  return {
    cents,
    canonical: `${Math.floor(cents / 100)}.${String(cents % 100).padStart(2, '0')}`,
    display: new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: 'EUR',
    }).format(cents / 100),
  };
}
