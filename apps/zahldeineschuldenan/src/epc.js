function clean(value) {
  return String(value ?? '').replace(/[\r\n]/g, ' ').trim();
}

export function createEpcPayload({ name, iban, bic, amount }) {
  const normalizedIban = clean(iban).replace(/\s/g, '').toUpperCase();
  const normalizedBic = clean(bic).replace(/\s/g, '').toUpperCase();
  if (!name || !/^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$/.test(normalizedIban)) {
    throw new Error('Payment recipient name or IBAN is not configured correctly.');
  }

  return [
    'BCD', '002', '1', 'SCT', normalizedBic, clean(name), normalizedIban,
    `EUR${amount.canonical}`, '', '', 'Schulden begleichen', '',
  ].join('\n');
}
