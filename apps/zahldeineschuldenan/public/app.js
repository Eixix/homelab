const data = window.PAYMENT_DATA;
const payment = document.querySelector('#payment');
const error = document.querySelector('#error');

const deobfuscate = ({ masked, key }) => {
  const maskedBytes = Uint8Array.from(atob(masked), character => character.charCodeAt(0));
  const keyBytes = Uint8Array.from(atob(key), character => character.charCodeAt(0));
  const plain = maskedBytes.map((byte, index) => byte ^ keyBytes[index]);
  return new TextDecoder().decode(plain);
};

document.querySelector('.money-rain').innerHTML = Array.from({ length: 18 }, (_, i) => {
  const drift = i % 2 ? 45 : -45;
  return `<span style="--x:${(i * 37) % 101}%;--delay:${i * -.73}s;--duration:${7 + (i % 6)}s;--drift:${drift}px;--spin:${300 + i * 23}deg">€</span>`;
}).join('');

if (!data) {
  error.hidden = false;
  const form = document.querySelector('#amount-form');
  const input = document.querySelector('#amount-input');
  const formError = document.querySelector('#amount-error');

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const value = input.value.trim().replace(',', '.');
    if (!/^\d+(?:\.\d{1,2})?$/.test(value) || Number(value) <= 0 || Number(value) > 999999.99) {
      formError.textContent = 'Bitte gib einen Betrag zwischen 0,01 € und 999.999,99 € ein.';
      input.setAttribute('aria-invalid', 'true');
      input.focus();
      return;
    }

    input.removeAttribute('aria-invalid');
    const canonical = Number(value).toFixed(2).replace('.', ',');
    window.location.assign(`/${encodeURIComponent(canonical)}/`);
  });
} else {
  const iban = deobfuscate(data.bankTransfer.ibanObfuscated);
  payment.hidden = false;
  document.querySelector('#amount').textContent = data.amount.display;
  document.querySelector('#paypal').href = data.paypalUrl;
  document.querySelector('#bank-recipient').textContent = data.bankTransfer.recipient;
  document.querySelector('#bank-iban').textContent = iban.replace(/(.{4})/g, '$1 ').trim();
  document.querySelector('#bank-amount').textContent = data.amount.display;
  document.querySelector('#bank-reference').textContent = data.bankTransfer.reference;
  document.querySelector('#qr').src = data.qr;

  document.querySelector('#show-bank').addEventListener('click', () => {
    const panel = document.querySelector('#bank-panel');
    panel.hidden = !panel.hidden;
    if (!panel.hidden) panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  });

  const copyStatus = document.querySelector('#copy-status');
  const copy = async (text, message) => {
    try {
      await navigator.clipboard.writeText(text);
      copyStatus.textContent = message;
    } catch {
      copyStatus.textContent = 'Kopieren nicht möglich – bitte die Daten oben markieren.';
    }
  };

  document.querySelector('#copy-iban').addEventListener('click', () =>
    copy(iban, 'IBAN kopiert. Jetzt Banking-App öffnen und einfügen.'));
  document.querySelector('#copy-all').addEventListener('click', () => copy([
    `Empfänger: ${data.bankTransfer.recipient}`,
    `IBAN: ${iban}`,
    data.bankTransfer.bic ? `BIC: ${data.bankTransfer.bic}` : null,
    `Betrag: ${data.amount.display}`,
    `Verwendungszweck: ${data.bankTransfer.reference}`,
  ].filter(Boolean).join('\n'), 'Alle Überweisungsdaten kopiert.'));
}
