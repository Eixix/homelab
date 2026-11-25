# Public traffic and anti-bot protection

Public services are reached through Cloudflare. The `cloudflare-only` middleware
checks the TCP peer against Cloudflare's published IPv4/IPv6 ranges **before**
any middleware trusts `CF-Connecting-IP`. Forwarded headers alone do not prove
that a request came through Cloudflare. Keep this allowlist synchronized with
both entrypoints' `forwardedheaders.trustedips` in `compose/core/traefik.yaml`
and https://www.cloudflare.com/ips/.

Cloudflare must send `CF-Connecting-IP`; do not enable the Remove visitor IP
headers transform. For original IPv6 identities, leave Pseudo IPv4 disabled or
use Add Header rather than Overwrite Headers. Requests to the affected public
routes directly from the LAN or origin IP receive 403; use an internal hostname
where one exists, or resolve the public hostname through Cloudflare. These
middlewares assume Traefik sees Cloudflare's actual peer IP, without another
NAT/proxy replacing it. Verify both IPv4 and IPv6 during deployment.

## Route policy

- Payment page, flag quiz, MTG oracle: Anubis challenges browser traffic. Anubis
  uses `CUSTOM_REAL_IP_HEADER=CF-Connecting-IP` and does not use Traefik's socket
  address as the visitor identity. The payment backend has `traefik.enable=false`;
  stopping Anubis must never expose an unchallenged backend route.
- Birthday (`30.betz.coffee`), tournament (`mtg.betz.coffee`), and SplitLedger's
  browser frontend (`money.betz.coffee`): central Anubis reverse proxies. Targets
  are `jump-to-birthday-web-1:80`, `magic_tournament:80`, and `splitledger-web:80`.
  The tournament's exact GET WebSocket upgrade path `/app/` has a higher-priority
  app route; ordinary HTTP requests still go through Anubis. SplitLedger's relay
  hostname is separate and keeps its app-facing route without a challenge.
- Shlink: browser rate limit, without an interactive challenge so redirects and
  link previews work.
- Immich (both public hosts), KitchenOwl, Vaultwarden and Home Assistant's public
  Alexa/auth routes: generous API rate limit, without browser challenges.
- Immich password login (`POST /api/auth/login`): separate stricter limit on both
  public hosts. Uploads, API-key access and token refreshes keep the API budget.
- Vaultwarden: its native login/2FA limiter uses `CF-Connecting-IP`, averaging one
  request per 60 seconds with a burst of 10; the router checks the Cloudflare peer.
- Actual banking callback: existing exact GET-only public route and 10/minute,
  burst-5 limiter, now keyed by `CF-Connecting-IP` after the Cloudflare peer check.
- Pizza: existing Bosch/owner CIDR restriction, now evaluated against the verified
  `CF-Connecting-IP` behind `cloudflare-only`. No browser challenge or new rate
  limit. The payment page uses the same header for Bosch styling, independent of
  Anubis rewriting `X-Forwarded-For`.
- Internal services: existing LAN-only policy, unchanged.

Traefik browser limits average 10 requests/second with a burst of 100. API limits
average 50 requests/second with a burst of 200. Immich password login averages
10 requests/minute with a burst of 10. These are request limits, not failed-login
counts. Each middleware shares its per-visitor budget across routes using it;
visitors behind the same public IP also share a budget. Excess requests receive
429. Large uploads count as requests, not bytes. Tune from observed 429s and
legitimate usage, especially photo synchronization and shared networks.

The Anubis policy keeps its existing exceptions for `/.well-known/*`, favicons,
`robots.txt` and `sitemap.xml`. Do not place sensitive application endpoints in
those namespaces. Noindex headers are advisory, not an access restriction.

A priority-900 file-provider guard for all five sibling browser hostnames sends
requests to the blackhole if their priority-1000 Anubis router is unavailable.
This prevents old priority-100 backend labels from becoming a bypass while
sibling deployment updates are pending. Their security branches disable those
browser backend routers entirely. The guard is intentionally independent of
Docker container health. Wedding and Examns are outside this deployment scope.

Unknown hosts, direct-IP catchalls and scanner paths retain the intentional
blackhole behavior. No changes to their destination, priorities or timeouts are
needed for this policy. Known public routes reject direct non-Cloudflare peers;
this is distinct from the unchanged unknown-host catchall.

## Validation and manual deployment

Validate before deployment:

```sh
docker compose --env-file .env --profile external config --quiet
```

Deploy manually using the normal workflow. Recreate the payment backend (to
remove its old Traefik labels), all three Anubis containers and the affected app
containers: `shlink`, `vaultwarden`, `kitchenowl-front`, `immich-server`,
`homeassistant`, `actual-server`, and `pizza`. The mounted dynamic configuration directory
is watched by Traefik; its static entrypoint configuration is unchanged.
All five sibling upstreams are managed outside this Compose project. Deploy
Anubis instances `anubis-birthday`, `anubis-tournament`, and `anubis-splitledger`
alongside the existing three. The file-provider guards also protect against old
backend routers until sibling deployments remove their labels.

The direct SSH deployment copies Git-managed files only and preserves existing
`.env`, `secrets/`, `data/`, and `backups/`. Do not replace runtime credentials
when deploying this protection. A proposed idempotent initialization change to
the GitHub workflow is retained locally in the ignored security-review backup;
the current GitHub OAuth token cannot publish workflow changes.

After deployment, verify browser access to all three Anubis sites, Immich login
on both public hosts, a mobile upload/sync, Vaultwarden login with 2FA, KitchenOwl,
a Shlink redirect, Alexa authorization and the banking callback. Check for
unexpected 403/429 responses. Verify that stopping the payment Anubis instance
in a maintenance window never serves the payment page directly, then restart it.
Do not print credentials, cookies or callback query strings in verification logs.
