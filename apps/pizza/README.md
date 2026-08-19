# Pizza-Fernschreiber

Private daily pizza ordering for the Bosch corporate network and explicitly
configured owner addresses. The application enforces the allowlist itself and
must only be exposed through the repository's trusted Traefik instance.

## Local production configuration

The deployed menu lives in `apps/pizza/config/menu.json`. Set these values in the
untracked `.env`:

```env
PIZZA_HOST=pizza.betz.coffee
PIZZA_OWNER_CIDRS=203.0.113.4/32
PIZZA_ADMIN_PASSWORD=replace-with-a-long-unique-password
PIZZA_COOKIE_SECRET=replace-with-at-least-32-random-bytes
PIZZA_PREVIEW_MODE=false
PIZZA_N8N_WEBHOOK_URL=http://n8n:5678/webhook/replace-me
PIZZA_N8N_WEBHOOK_SECRET=replace-with-a-shared-bearer-secret
```

Generate the cookie secret with `openssl rand -base64 48`. Multiple owner CIDRs
may be separated with spaces or commas. `PIZZA_BOSCH_CIDRS` can override the
default list in Compose.

For a new scraped text menu, run:

```console
node apps/pizza/scripts/convert-menu.js pizzakarte.txt apps/pizza/config/menu.json
```

The loader also supports the original text format. Each item uses:

```text
Category | Item name | 12,50 | Optional description
```

`@restaurant=` and `@website=` set the heading/footer destination. Item order is
stable and is therefore significant: changing the menu while a daily session is
open is unsupported.

## n8n contract

The app POSTs JSON with an `event` field. Values are `order_created`,
`order_updated`, `order_cancelled`, and `daily_summary`. Configure the n8n Webhook
node to accept POST and, when a shared secret is configured, require the
`Authorization: Bearer …` header. Immediate events include the order and total.
The 10:30 summary contains every order, grouped item quantities, per-person
totals, and the grand total.

The app retries a failed daily summary every 30 seconds until n8n accepts it.
The admin dashboard can also request a retry. n8n should use the event and date
as an idempotency key before sending Telegram, since a network timeout can occur
after n8n accepted the request.

For an after-hours local UI preview only, `PIZZA_PREVIEW_MODE=true` disables the
10:30 deadline. To preview the complete flow through the normal homelab stack, set
`PIZZA_PREVIEW_MODE=true` only in the local `.env`, then run the normal root
Compose project. Production must leave it `false`.

## Network source

The initial German Bosch list is based on prefixes associated with AS9183. The
large `139.15.0.0/16` aggregate and the smaller registered blocks are included;
IPv6 uses Bosch's `2a03:cc00::/32` allocation. Ownership and actual office egress
can change, so verify the source address from a Bosch workstation before launch
and review the configured list periodically.

## Payment handoff

After submission, the browser links to `zahldeineschuldenan` with both the exact
amount and a `Pizza YYYY-MM-DD – Name` payment reference. The payment app now
uses that reference in its display, clipboard data, and EPC/GiroCode payload.
