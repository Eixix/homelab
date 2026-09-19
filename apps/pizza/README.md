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

## Pizza extras

`menu.json` defines priced options in `extraGroups`; regular pizza items reference
the `pizza` group using `extraGroup`. The 52 options (including wholemeal dough)
were copied from the supplied Lieferando Margherita options in `extras.txt`.
Surcharges are used as listed, without an additional promotional discount.
Vegan and party pizzas have no extras configured because their option prices
have not been supplied.

Each selected pizza has its own extras selector and total. Requests send
`extraIds` on each order line; the server validates them against that item's
options and snapshots their names and prices. `priceCents` includes extras per
pizza. Saved orders, admin listings and webhook item names include the toppings;
daily summaries group only matching configurations and prices. Existing orders
without extras remain supported. Keep the menu fixed during an open session.

The text conversion script replaces the catalog; preserve `extraGroups` and item
`extraGroup` references if regenerating the menu with that script.

### Cheaper equivalent pizzas

`config/pizza-equivalences.json` maps explicit menu recipes to Margherita extras.
Before submission, a confirmation popup offers cheaper mapped combinations and
shows the saving per pizza. Accepting replaces matching configurations in the
form and submitted order; declining keeps the original. Additional toppings and
dough choices are preserved. Combinations requiring double portions of the same
extra, ambiguous ingredients, or more than 20 Margheritas are not suggested.

Prices are recalculated from the loaded catalog. Recipe names/descriptions guard
against reusing a connection after a menu change; review these mappings when
updating recipes. These are menu-based ingredient matches, not restaurant
confirmation of identical topping portions. The mapping ships in the image,
so changes require rebuilding the pizza service.

The same visual theme is used for all allowed networks, including Bosch.

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

## Availability and live updates

The admin menu can switch the Margherita deal off and set its regular price
(default €10.40). With the deal enabled, the catalog price (€9.36) applies.
The setting is persisted across days and restarts. Extras retain their listed
prices; cheaper-pizza suggestions use the active price. Existing orders retain
their saved prices; edits use current prices. The browser sends its quoted total
so a price change during submission is rejected rather than silently charged.

Both pages refresh state every 15 seconds and when returning to a visible tab.
The ordering page preserves draft names, quantities and toppings. It announces
ordering status and the admin's “Pizza ist da!” message, including on the packed
order view. Arrival can be withdrawn and resets on the next Berlin calendar day.
A connection warning appears if updates fail. No new n8n events are sent.

## Optional browser push notifications

Users can choose “Benachrichtigungen einschalten” and grant browser permission to
receive ordering-open and pizza-arrival notifications even with the page closed.
The same button turns them off again. Each event is announced at most once per
Berlin calendar day; reopening orders or toggling arrival does not send duplicates.
Notifications contain only the announcement, never names or order details.
Clicking one focuses the existing page without losing its draft, or opens the site.

Push requires HTTPS, browser/OS notification support and permission. On iPhone
and iPad, add the site to the Home Screen and open it there before subscribing
([Apple guidance](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/)).
Delivery depends on the browser/OS and network; the app does not guarantee delivery
when the browser is force-quit or notifications are blocked by device policy.
The manifest enables Home Screen installation. The service worker handles push
only; it does not cache private pages or bypass the IP allowlist. Opening the site
or changing subscriptions still requires access from an allowed network.

No new environment secrets are required. With the existing `PIZZA_HOST` set,
the app creates VAPID keys once and saves them and device subscriptions in the
private runtime `orders.json` (`PIZZA_DATA_PATH`, mode 0600). Preserve this file
across deploys/restarts and include it in protected backups. Never commit it or
log subscription URLs or private keys. If the keys are lost, users need to visit
the page and enable notifications again. Without `PIZZA_HOST`, push is disabled.

Outbound HTTPS must reach the browser push providers (Google FCM, Mozilla,
Apple or Windows). Subscription endpoints are restricted to these providers;
expired subscriptions are removed on HTTP 404/410. Requests use a five-second
socket timeout and a five-minute delivery TTL to limit stale announcements.
The admin page reports accepted, failed and expired sends; accepted means the
push service accepted the message, not that a device displayed it. Delivery is
best effort: failed or interrupted broadcasts are not automatically retried,
to avoid sending duplicate or outdated announcements. The live page status
continues to update independently.

After manual deployment, verify opt-in on a supported browser, close its page,
and use the admin opening/arrival controls to check delivery and click-through.
Then disable notifications on the device and confirm it receives no later alerts.
