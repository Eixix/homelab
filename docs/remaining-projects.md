# Remaining Projects

These services are still running on the production Docker host but are not fully managed by this repository. Keep this page public-safe: record hostnames, data paths, and migration intent, but never copy real credentials, tokens, webhook URLs, or BasicAuth hashes from live labels.

## Portainer-Origin Apps

| Project | Containers | Route | State | Data | Recommended next action |
| --- | --- | --- | --- | --- | --- |
| Leantime | `leantime-leantime-1`, `mysql_leantime` | `https://projekt.betz.coffee` | Running | `/docker-compose-services/leantime/{userfiles,plugins,public_userfiles,database}` | Decide whether the external project-management route is still needed before porting. If kept, migrate app files and MySQL together. |
| Stirling PDF | `stirling` | `https://pdf.home` | Running but reported unhealthy during inventory | `/docker-compose-data/stirling-data/*` | Either retire it or port with a health-check fix; do not treat the current unhealthy state as a clean baseline. |
| Sili bot | `sili-bot` | None observed | Running | Docker volume `silibotvolume` | Decide ownership first. It has no Traefik route, so it may belong outside the web stack. |

## Retired During Migration

| Project | Former route | Retired state | Preserved data |
| --- | --- | --- | --- |
| Mealie | `https://food.home` | Container removed; Traefik no longer exposes the `food` router. | `/docker-compose-services/mealie-data` is preserved until an explicit data purge decision. |

## Independent GitHub-User Projects

These already appear to live under `/home/github/<project>` and may be better kept as independent deployments unless they should share this repo's backup and operational model.

| Project | Containers | Route | State | Data | Recommended next action |
| --- | --- | --- | --- | --- | --- |
| MTG tournament | `magic_tournament` | `https://mtg.betz.coffee` and websocket path `/app` | Running | `/docker-compose-services/mtg/database/database.sqlite`, `/docker-compose-services/mtg/storage/app` | Keep as independent GitHub deployment unless the app is now homelab-owned. It has a BasicAuth Traefik label; do not copy that hash into this public repo. |
| MTG hand oracle | `mtg-hand-oracle` | `https://mtg-oracle.betz.coffee` | Running | No mounts observed | Keep independent; no persistent data was observed. |
| SplitLedger | `splitledger-web`, `splitledger-relay` | `https://money.betz.coffee`, `https://relay.betz.coffee` | Running | `/docker-compose-services/splitledger-data` | Keep independent unless backups should move into the homelab repo model. If kept independent, document its backup owner. |
| FollowUp | `followup_frontend`, `followup_tor_frontend` | No Traefik route observed in the new proxy | Running | `/home/github/followup-tor-frontend-data` | Verify whether it is intentionally route-less or exposed elsewhere. If it is not used, retire it after data review. |

## Already Confirmed Absent

The following were not observed as running containers during the production inventory: Audiobookshelf, EVCC, Ghostfolio, Scrypted, Uptime Kuma, Open WebUI, Ollama, Docker Registry, and WUD.
