const data = window.PAYMENT_DATA;
const payment = document.querySelector('#payment');
const error = document.querySelector('#error');

document.querySelector('.money-rain').innerHTML = Array.from({ length: 18 }, (_, i) => {
  const drift = i % 2 ? 45 : -45;
  return `<span style="--x:${(i * 37) % 101}%;--delay:${i * -.73}s;--duration:${7 + (i % 6)}s;--drift:${drift}px;--spin:${300 + i * 23}deg">€</span>`;
}).join('');

if (!data) {
  error.hidden = false;
} else {
  payment.hidden = false;
  document.querySelector('#amount').textContent = data.amount.display;
  document.querySelector('#paypal').href = data.paypalUrl;
  document.querySelector('#qr').src = data.qr;
  document.querySelector('#show-qr').addEventListener('click', () => {
    const panel = document.querySelector('#qr-panel');
    panel.hidden = !panel.hidden;
    if (!panel.hidden) panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  });
}
