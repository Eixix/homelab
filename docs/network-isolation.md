# Network Isolation

The current production network model is deliberately simple:

- `external_network`: public Traefik-facing services.
- `internal_network`: LAN-only services and most private app backends.
- `network_mode: host`: only where the service genuinely needs host networking, currently Home Assistant, Beszel Agent, and Cloudflare DDNS.

This was a good migration target because it kept the cutover understandable and let Traefik continue to discover retained legacy containers. It is not the final hardening model.

## Target Model

Prefer one small network boundary per application stack:

- A shared `traefik_public` or `traefik_internal` edge network for services Traefik must reach.
- A private backend network per multi-container app, for example `paperless_backend`, `immich_backend`, and `shlink_backend`.
- Databases, brokers, Redis, and machine-learning workers stay only on their app backend network.
- The app's web/API container joins both its app backend network and the relevant Traefik edge network.
- Single-container apps can stay on only the relevant Traefik edge network unless they need private peers.

This means Traefik can reach the web surface, but unrelated apps cannot casually connect to each other's databases or brokers.

## Do Not Split Blindly

Do not create one network per container just for symmetry. The useful boundary is the trust boundary:

- Services that must talk to each other share a private network.
- Services that do not need to talk should not share a backend network.
- Traefik joins many edge networks by design, so it remains a high-trust component.
- Host-network services need host firewalling and application config, because Docker networks do not isolate them.

## Suggested Order

1. Start with database-backed apps: Paperless, Immich, Shlink.
2. Then split KitchenOwl frontend/backend if needed.
3. Leave Home Assistant, Beszel Agent, and Cloudflare DDNS as host-network exceptions.
4. After each split, deploy only that service set and verify app login plus Traefik routing.

This is post-migration hardening, not a migration blocker.
