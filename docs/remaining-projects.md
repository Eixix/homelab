# Remaining Projects

These services are still running on the production Docker host but are not fully managed by this repository. Keep this page public-safe: record hostnames, data paths, and migration intent, but never copy real credentials, tokens, webhook URLs, or BasicAuth hashes from live labels.

## Portainer-Origin Apps

| Project | Containers | Route | State | Data | Recommended next action |
| --- | --- | --- | --- | --- | --- |
| Sili bot | `sili-bot` | None observed | Running | Docker volume `silibotvolume` | Keep independent in `Eixix/sili-telegram-bot`; its deploy workflow still exists. Fix that repo's `docker run` command so `--restart unless-stopped` is passed before the image name. |

## Retired During Migration

| Project | Former route | Retired state | Preserved data |
| --- | --- | --- | --- |
| Mealie | `https://food.home` | Container removed; Traefik no longer exposes the `food` router. | `/docker-compose-services/mealie-data` is preserved until an explicit data purge decision. |
| Leantime | `https://projekt.betz.coffee` | App and MySQL containers removed; Traefik no longer exposes the `leantime` router, and the hostname now falls through to the external blackhole. | `/docker-compose-services/leantime` is preserved until an explicit data purge decision. |
| Stirling PDF | `https://pdf.home` | Container removed; Traefik no longer exposes the `stirling` router. | `/docker-compose-data/stirling-data` is preserved until an explicit data purge decision. |

## Independent GitHub-User Projects

These already appear to live under `/home/github/<project>` and may be better kept as independent deployments unless they should share this repo's backup and operational model.

| Project | Containers | Route | State | Data | Recommended next action |
| --- | --- | --- | --- | --- | --- |
| MTG tournament | `magic_tournament` | `https://mtg.betz.coffee` and websocket path `/app` | Running | `/docker-compose-services/mtg/database/database.sqlite`, `/docker-compose-services/mtg/storage/app` | Keep independent in its own GitHub/org deployment. It has a BasicAuth Traefik label; do not copy that hash into this public repo. |
| MTG hand oracle | `mtg-hand-oracle` | `https://mtg-oracle.betz.coffee` | Running | No mounts observed | Keep independent in `Tobael/mtg-hand-oracle`; its deploy workflow uses `docker compose up -d --build --remove-orphans` and Compose already sets `restart: unless-stopped`. |
| SplitLedger | `splitledger-web`, `splitledger-relay` | `https://money.betz.coffee`, `https://relay.betz.coffee` | Running | `/docker-compose-services/splitledger-data` | Keep independent like MTG. The live containers still reference `/home/github/splitledger/docker-compose.yml`, but that checkout was not present during inventory, so restore or verify its separate deployment path before changing it. |
| FollowUp | `followup_frontend`, `followup_tor_frontend` | No Traefik route observed in the new proxy; Tor frontend container is running | Running | `/home/github/followup-tor-frontend-data` | Keep independent in `Eixix/followup`. The local repo has a deploy workflow and Compose restart policies, but the live containers reference `/home/github/followup/dockerfiles/compose.yml` and that checkout was not present during inventory, so restore or verify the separate deployment path before changing it. |

## Independent Checkout Recovery

The SplitLedger and FollowUp containers are healthy enough to keep running, but their deployment checkouts were not present under `/home/github` during inventory. Because `/home/github` is owned by the `github` deployment user, restore those paths through their own deploy pipelines instead of hand-copying files with the `tobias` SSH account.

For FollowUp, trigger `Eixix/followup`'s deploy workflow. A no-code deploy-trigger commit is enough when using a workstation with push access:

```bash
cd /home/tobias/Projects/followup
git status --short
git commit --allow-empty -m "Trigger FollowUp redeploy"
git push
```

The workflow rsyncs the repo to `/home/github/followup/` and runs `docker compose up -d --build --remove-orphans` from `dockerfiles/`.

For SplitLedger, first identify or restore the owning repo/deploy workflow, then trigger that pipeline so `/home/github/splitledger/docker-compose.yml` exists again. Do not recreate the path from this public homelab repo unless SplitLedger is deliberately moved under homelab ownership.

## Already Confirmed Absent

The following were not observed as running containers during the production inventory: Audiobookshelf, EVCC, Ghostfolio, Scrypted, Uptime Kuma, Open WebUI, Ollama, Docker Registry, and WUD.
