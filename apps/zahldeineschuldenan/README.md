# Zahl deine Schulden an Tobias

A small payment link page. The URL path is the requested EUR amount:

```text
https://zahldeineschuldenantobias.betz.coffee/12,50/
```

The page offers PayPal.Me and an EPC/GiroCode QR for banking apps. Amounts must
be positive, use at most two decimal places, and are limited to `999999.99` EUR.
Every response carries an `X-Robots-Tag` that forbids indexing, and
`robots.txt` disallows crawling the entire host.

For same-device mobile payments, the page displays the transfer details and
offers buttons to copy either the IBAN or the complete transfer. The QR code is
kept behind an expandable section for scanning from a second device.

If the URL contains no valid amount, the page displays an amount field and
redirects the visitor to the corresponding amount URL after validation.

## Configuration

Set these only in the ignored repository-root `.env`:

```dotenv
ZAHLDEINESCHULDENAN_HOST=zahldeineschuldenantobias.betz.coffee
PAYMENT_RECIPIENT_NAME=Your account holder name
PAYMENT_IBAN=DE...
PAYMENT_BIC=...
PAYPAL_ME_NAME=YourPayPalMeName
```

## Local checks

```sh
npm --prefix apps/zahldeineschuldenan test
docker compose --env-file .env --profile external config --quiet
docker compose --env-file .env build zahldeineschuldenan
```

For production, select `zahldeineschuldenan` in the manual deploy workflow.
The workflow pulls registry-backed services and builds services with a local
`build:` definition before recreating them.
