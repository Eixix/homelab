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
The flag quiz and MTG oracle upstreams are managed outside this Compose project;
check their deployed labels separately for any direct router that could bypass
Anubis. Nothing in this repository can exclude such an out-of-repository route.

After deployment, verify browser access to all three Anubis sites, Immich login
on both public hosts, a mobile upload/sync, Vaultwarden login with 2FA, KitchenOwl,
a Shlink redirect, Alexa authorization and the banking callback. Check for
unexpected 403/429 responses. Verify that stopping the payment Anubis instance
in a maintenance window never serves the payment page directly, then restart it.
Do not print credentials, cookies or callback query strings in verification logs.
