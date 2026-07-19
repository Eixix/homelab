# Homelab Docker Repo

Ziel: laufende Docker-Konfiguration schrittweise in ein Git-basiertes Compose-Setup migrieren, mit sauberem Secret-Handling, dynamischen Hostnames, Traefik und testbarer Backupstrategie.

## Lokaler Start

```bash
cp .env.local.example .env
mkdir -p secrets backups data/traefik/letsencrypt
chmod 700 secrets
printf 'dummy-local-token' > secrets/cloudflare_api_token
chmod 600 secrets/cloudflare_api_token

docker network create external_network || true
docker network create internal_network || true

docker compose config
docker compose up -d step-ca reverse-proxy homepage adguardhome
```

Lokale URLs werden aus `.env` gebaut. Interne lokale Hosts nutzen eine punktierte `.home.localhost`-Zone. Externe lokale Test-Hosts nutzen `.betz.localhost`.

```text
https://homepage.home.localhost
https://docs.home.localhost
https://traefik.home.localhost
https://adguard.home.localhost
https://budget.home.localhost
https://n8n.home.localhost
https://go2rtc.home.localhost
https://dokumente.home.localhost
https://hass.home.localhost
https://fotos.home.localhost
https://reader.home.localhost
https://beszel.home.localhost
https://shlink.home.localhost
https://shopping.betz.localhost
https://fotos.betz.localhost
https://hass.betz.localhost/auth
https://hass.betz.localhost/api/alexa
https://passwort.betz.localhost
https://l.betz.localhost
https://ca.localhost:9000
```

Homepage nutzt Environment-Variablen aus `compose/apps/homepage.yaml`, damit dieselbe Konfiguration lokal und produktiv funktioniert.

Der lokale Step-CA-Name ist `Homelab Local Development CA`; produktiv wird fuer frische CA-Daten `Homelab Internal CA` verwendet. Eine bestehende CA unter `data/step-ca` behaelt ihren urspruenglichen Namen, bis diese Runtime-Daten bewusst neu erzeugt werden.

`cloudflare-ddns` startet lokal nicht automatisch, weil er im Profil `external` liegt. Produktiv startest du ihn mit:

```bash
docker compose --profile external up -d cloudflare-ddns
```

`beszel-agent` liegt im Profil `agent`, damit lokale Starts mit Platzhalter-Keys sauber bleiben. Produktiv startest du ihn nach dem Setzen von `BESZEL_AGENT_KEY` und `BESZEL_AGENT_TOKEN` mit:

```bash
docker compose --profile agent up -d beszel-agent
```

## Produktiver Start auf dem Server

```bash
cp .env.example .env
nano .env
mkdir -p secrets backups data/traefik/letsencrypt
chmod 700 secrets
printf 'NEUER_CLOUDFLARE_TOKEN_HIER' > secrets/cloudflare_api_token
chmod 600 secrets/cloudflare_api_token
```

Wichtig: Der alte Cloudflare Token aus der bisherigen Compose-Datei muss rotiert werden.

## GitHub Deployment

The deployment workflow copies the repository to `/home/github/homelab`. It preserves the remote `.env`, `secrets/`, `data/`, and `backups/` directories while synchronizing code and configuration. `SSH_USER` must be the `github` user that owns this directory and has Docker access.

Configure these GitHub Actions secrets before enabling a production deployment:

- `WIREGUARD_CONF`: WireGuard client configuration used by the runner to reach the server.
- `SSH_HOST`: server hostname or WireGuard address.
- `SSH_USER`: `github`.
- `DEPLOY_SECRET_KEY`: private SSH key for the `github` user.
- `SSH_KNOWN_HOSTS`: pinned known-host entry for `SSH_HOST`.
- `ENV_FILE`: complete production `.env` content.
- `CLOUDFLARE_API_TOKEN`: value written to `secrets/cloudflare_api_token`.

Set the `*_UID` and `*_GID` entries in `ENV_FILE` to values that can write the `github` user's `data/` directory, or align directory ownership accordingly. The workflow remains manual-only and validates the rendered production Compose configuration before changing containers.

The `services` workflow input accepts space-separated Compose service names. Leave it empty to synchronize and validate without starting anything. Use the reserved value `all` on its own to pull updates, rebuild, and redeploy the complete stack with every Compose profile enabled, including `external` and the Beszel `agent` profile.

Each workflow run records the containers that were actually created or recreated in the GitHub Actions job summary. An unchanged deployment reports `(none)`.

The production backup setup and restore outline are documented in [`docs/backup.md`](docs/backup.md).

## Validieren

```bash
docker compose config
docker compose pull
docker compose up -d step-ca reverse-proxy homepage
```

## Migrationsprinzip

1. Repo parallel zum alten Stack aufbauen.
2. Service-Dateien modular replizieren.
3. Secrets aus Compose entfernen.
4. Alle Hostnames nur über `.env` steuern.
5. Traefik ohne insecure dashboard testen.
6. Dienste nach und nach als Compose-Dateien exportieren/nachbauen.
7. Erst nach Restore- und Smoke-Test den alten Stand ersetzen.

## Services Migrieren

Neue App-Dateien liegen unter `compose/apps/`, Core-Infrastruktur unter `compose/core/`. Für jeden migrierten Dienst:

1. Hostname in `.env.example`, `.env.local.example` und lokaler `.env` ergänzen.
2. Compose-Datei in `compose/apps/<service>.yaml` anlegen.
3. Datei in `compose.yaml` unter `include` eintragen.
4. Router zuerst mit `lan-only@file,security-headers@file` starten.
5. `docker compose config --quiet` ausführen.

Persistente Daten liegen standardmäßig unter `data/<service>` im Repo-Root. Alte Pfade wie `/docker-compose-services/<service>` werden nur übernommen, wenn ein Dienst bewusst während der Migration weiter auf bestehende Produktivdaten zeigen soll.

Die laufende Produktions-Checkliste liegt in `docs/prod-migration-todo.md` und wird beim Portieren aktualisiert.
