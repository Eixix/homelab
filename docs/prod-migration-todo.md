# Production Migration TODO

Keep this list current while porting services. Check items only after they are validated against the production host, not just local compose rendering.

## Core

- [x] Use top-level `data/<service>` paths for new services.
- [x] Remove Portainer from the new stack.
- [x] Use dotted local test domains: `*.home.localhost` and `*.betz.localhost`.
- [x] Keep prod internal routes on `*.home` and prod external routes on `*.betz.coffee`.
- [x] Remove Authelia: no app router used it, and application-local authentication remains the chosen model.
- [x] Move mounted Homepage and Traefik dynamic config under `config/`.
- [x] Remove stale ignored runtime files left from the old `compose/traefik/letsencrypt` path after confirming they are not needed.
- [x] Migrate `/docker/step-ca` into `data/step-ca` and preserve the existing CA identity unless a deliberate regeneration is approved.
- [x] Migrate `/docker/letsencrypt` into `data/traefik/letsencrypt`.
- [x] Migrate `/docker/adguardhome` into `data/adguardhome/{work,conf}`.
- [x] Migrate `/docker/certificates/cloudflare.{crt,key}` into `data/traefik/certificates/` with the private key mode set to `600`.
- [x] Pre-stage copied current core and app data into `/home/github/homelab/data`; database-backed services still need a final stopped sync during their service cutover.
- [x] Verify the Cloudflare origin certificate remains the default Traefik certificate for `*.betz.coffee`; it currently expires in 2040.
- [x] Verify the Cloudflare ACME token cannot issue a certificate for `fotos.fabian-und-kristina.de`; keep that route off the Cloudflare DNS resolver unless that zone is added.
- [ ] Rotate Cloudflare token and write it to `secrets/cloudflare_api_token`.
- [ ] Replace all placeholder DB/app secrets in production `.env`.
- [ ] Decide whether to regenerate production Step CA data for the final `STEP_CA_INIT_NAME`.
- [x] Verify production DNS for `*.home` through AdGuard/hosts and `*.betz.coffee` through Cloudflare/DDNS.
- [x] Validate the staged production configuration with `docker compose --env-file .env --profile external config --quiet`.
- [x] Re-validate GitHub Actions staging deployment after adding legacy Homepage and Immich hostnames.
- [x] Run `docker compose --profile external up -d cloudflare-ddns` only on production.
- [x] Deploy the repository to `/home/github/homelab`; preserve `.env`, `secrets/`, `data/`, and `backups/` during code synchronization.
- [x] Configure GitHub Actions deployment secrets, including the pinned `SSH_KNOWN_HOSTS`, production `.env`, and Cloudflare API token.
- [x] Keep the GitHub Actions production deployment manual-only until the staged migration is complete.
- [ ] Configure `/etc/homelab-backup.env` and a protected GPG passphrase file, then test a backup and restore of the new `backup.sh`.
- [ ] Update the host backup job to invoke `/home/github/homelab/backup.sh`; retain the separate `/storage_array` backup job.
- [ ] Backup verification: run a restore drill from the new encrypted homelab backup and confirm database/app state before relying on it.

## Post-Migration Cleanup

- [ ] Add custom internal-only Traefik error pages with a clean minimalist design.
- [ ] Configure external unmatched `*.betz.coffee` traffic to time out or otherwise not respond instead of showing a default/not-found response.
- [ ] Clean up repository-local stale runtime/data artifacts that are no longer needed after the migration.
- [ ] Clean up production server legacy containers, old Compose directories, and abandoned mount data after each retained service has an explicit owner or rollback window has expired.

## Ported Services

- [x] Homepage: local route tested.
- [x] Vaultwarden: local route tested.
- [x] Shlink API and web client: local routes tested.
- [x] Actual Budget: local route tested.
- [x] n8n: local route tested.
- [x] go2rtc: local route tested.
- [x] KitchenOwl: local route tested.
- [x] Paperless-ngx: local route tested.
- [x] Home Assistant: local internal route tested.
- [x] Home Assistant: local external Alexa/auth route reaches Home Assistant.
- [x] Kavita: local route tested.
- [x] Immich: local internal route tested.
- [x] Immich: local external route tested.
- [x] Beszel monitoring: local route tested.
- [x] Vaultwarden: keep the admin page disabled in production by omitting `ADMIN_TOKEN`; use config/data changes for maintenance unless an explicit admin-window is needed.
- [x] Vaultwarden: stop legacy container, final-sync `/docker-compose-services/vaultwarden` into `data/vaultwarden`, and start the Git-managed service.
- [x] Vaultwarden: smoke test `https://passwort.betz.coffee` through Traefik.
- [x] Vaultwarden: verify browser extension/mobile sync after the Git-managed cutover.
- [x] Shlink: preserve existing production DB credentials for the migration; rotate after the service is stable.
- [x] Shlink: stop legacy containers, final-sync `/docker-compose-services/shlink/db_data` into `data/shlink/db`, and start the Git-managed API/web/database services.
- [x] Shlink: smoke test `https://l.betz.coffee` and `https://shlink.home`.
- [x] Shlink: create/verify API key for Shlink web client access.

## Other Running Projects

The current production Traefik also routes projects that are not represented in this repository. Do not retire it until each retained route has an explicit owner and proxy path.

- [ ] Validate a replacement Traefik can discover the still-running legacy containers attached to `internal_network` or `external_network` before the port 80/443 handover.
- [x] Migrate Home Assistant in the same cutover window instead of adding a temporary legacy host-network router.
- [x] Keep the legacy `fotos.fabian-und-kristina.de` Immich hostname; it now uses the external ACME resolver.
- [x] Exclude Wedding from this repository migration; it is deployed through its own GitHub pipeline.
- [x] Redirect the old `dashboard.home` Homepage hostname to `homepage.home`.
- [x] Remove or disable Traefik labels on legacy Wedding containers after confirming the separate GitHub deployment owns those routes; the old containers are stopped and renamed to `*_legacy_git_cutover`.
- [ ] Intentionally retire the old Portainer, Grafana, Prometheus, and WUD routes during the cutover.
- [ ] Decide the future of the currently separate Mealie, Leantime, Stirling PDF, Audiobookshelf, EVCC, Ghostfolio, Scrypted, Uptime Kuma, Open WebUI, Ollama, Docker Registry, and WUD projects.
- [ ] Decide the future of independent GitHub-user projects currently behind the old proxy, including MTG, SplitLedger, and FollowUp.
- [ ] Keep the old Traefik running until every retained service above has migrated to the new proxy or another explicit ingress.

## Newly Ported, Needs Production Verification

- [x] Kavita: migrate `/docker-compose-services/kavita/data` into `data/kavita/config`.
- [x] Kavita: verify production library mounts `KAVITA_BOOKS_PATH` and `KAVITA_COMICS_PATH`.
- [x] Kavita: smoke test `https://reader.home`.
- [x] Immich: preserve existing production DB credentials for migration compatibility; rotate after the service is stable.
- [x] Immich: preserve `IMMICH_UPLOAD_PATH=/storage_array/Photos`; it contains the production photo library and is backed up by the storage-array job.
- [x] Immich: migrate `/docker-compose-services/immich/database` into `data/immich/database`.
- [x] Immich: migrate `/docker-compose-services/immich/model-cache` into `data/immich/model-cache`.
- [x] Immich: enable Redis-friendly memory overcommit on the production host if not already set.
- [x] Immich: keep the old additional external hostname `fotos.fabian-und-kristina.de`.
- [x] Immich: smoke test `https://fotos.home`, `https://fotos.betz.coffee`, and `https://fotos.fabian-und-kristina.de`.
- [x] Monitoring: use non-placeholder Beszel agent key/token for migration; rotate exposed values after the service is stable.
- [x] Monitoring: start `beszel-agent` in production with `docker compose --profile agent up -d beszel-agent`.
- [x] Monitoring: migrate `/docker-compose-services/beszel_data` and socket data into `data/monitoring/beszel`.
- [x] Monitoring: verify `BESZEL_EXTRA_FILESYSTEM_PATH` on production.
- [x] Monitoring: smoke test `https://beszel.home`.
- [x] Actual Budget: stop legacy container, final-sync `/docker-compose-services/actual/data` into `data/actual`, and start the Git-managed service.
- [x] Actual Budget: smoke test `https://budget.home`.
- [x] n8n: stop legacy container, final-sync `/docker-compose-services/n8n` into `data/n8n`, and start the Git-managed service.
- [x] n8n: verify webhook/editor URLs after prod hostname cutover.
- [ ] n8n: decide whether production needs external task runners for Python-capable executions.
- [x] go2rtc: stop legacy container, final-sync `/docker-compose-services/go2rtc` into `data/go2rtc`, and start the Git-managed service.
- [x] go2rtc: verify camera config, WebRTC/RTSP access, and whether privileged mode is still required.
- [x] go2rtc: smoke test `https://go2rtc.home`.
- [x] KitchenOwl: stop legacy containers, final-sync `/docker-compose-services/kitchenowl-data` into `data/kitchenowl`, and start the Git-managed frontend/backend services.
- [x] KitchenOwl: smoke test `https://shopping.betz.coffee` and confirm frontend/backend login flow.
- [x] Paperless-ngx: replace placeholder DB, secret key, and admin password values.
- [x] Paperless-ngx: migrate `/docker-compose-services/paperless-*` data into `data/paperless/*`.
- [x] Paperless-ngx: verify production consume mount points `PAPERLESS_CONSUME_PATH` at `/storage_array/documents`.
- [x] Paperless-ngx: enable Redis-friendly memory overcommit on the production host if not already set.
- [x] Paperless-ngx: retire the old Outlook OAuth integration during migration.
- [x] Paperless-ngx: smoke test `https://dokumente.home`.
- [x] Home Assistant: migrate `/docker-compose-services/homeassistant` into `data/homeassistant`.
- [x] Home Assistant: preserve `.storage` authentication data, users, roles, MFA settings, and long-lived access tokens during the data migration.
- [x] Home Assistant: verify `http:` trusted proxy settings for Traefik in `configuration.yaml`.
- [x] Home Assistant: smoke test full UI at `https://hass.home`.
- [x] Home Assistant: smoke test actual Alexa/auth flow at `https://hass.betz.coffee`; local fresh config only verifies routing.

## Production Core Verification

- [x] Step CA is running from the Git-managed stack and reports healthy.
- [x] Traefik is running from the Git-managed stack on ports `80` and `443`.
- [x] AdGuard Home DNS is running on `10.0.0.2:53`.
- [x] AdGuard Home UI works through Traefik at `https://adguard.home` using the migrated web port `3125`.
- [x] Cloudflare DDNS runs from the Git-managed stack and reports `*.betz.coffee` and `betz.coffee` records are up to date.

## Production App Verification

- [x] Homepage: rename the legacy Portainer-managed `homepage` container to `homepage_legacy_git_cutover`.
- [x] Homepage: start the Git-managed `homepage` service through the deploy workflow.
- [x] Homepage: smoke test `https://homepage.home`.
- [x] Homepage: smoke test `https://dashboard.home` redirects to `https://homepage.home`.

## Production Cutover

- [ ] Stop old container for a service before starting the new one on the same hostname.
- [ ] Back up old service data before migration.
- [ ] Restore/copy data into the matching `data/<service>` folder.
- [ ] Set copied bind-mount ownership to the UID/GID required by the new service before starting it; the production deployment user is `github` (`1003:1003`).
- [ ] Start only the migrated service and its dependencies.
- [ ] Smoke test local/internal route.
- [ ] Smoke test external route where applicable.
- [ ] Verify Traefik serves the intended certificate.
- [ ] Verify logs have no startup migration errors.
- [ ] Only then remove or archive old service definition.
