# Homelab Docker Repo

Modulares Docker-Compose-Setup mit Traefik als zentralem Reverse Proxy, getrennten internen und öffentlichen Zugängen sowie gemeinsamem Deployment und Backup.

## Aufbau

| Pfad | Aufgabe |
| --- | --- |
| `compose.yaml` | Einstiegspunkt; bindet Services ein und definiert gemeinsame Netzwerke und Secrets. |
| `compose/core/` | Infrastruktur wie Reverse Proxy, Zertifizierungsstelle und DNS. |
| `compose/apps/` | Compose-Dateien der einzelnen Anwendungen. |
| `config/` | Versionierte Konfiguration, unter anderem Traefik-Middlewares. |
| `apps/` | Quellcode und Dockerfiles eigener Anwendungen. |
| `data/<service>/` | Persistente Laufzeitdaten, nicht in Git. |
| `secrets/`, `.env` | Lokale Zugangsdaten und umgebungsspezifische Werte, nicht in Git. |
| `backups/` | Lokale Backupartefakte, nicht in Git. |
| `docs/` | Betriebsanleitungen und technische Details. |

## Traefik und Netzwerke

Traefik läuft als Compose-Service `reverse-proxy` mit dem Containernamen `traefik` und nimmt HTTP/HTTPS auf Port 80/443 entgegen. HTTP wird auf HTTPS umgeleitet. Docker-Labels legen Host-Regeln, Zielports, TLS und Middlewares fest; Services werden nur mit `traefik.enable=true` veröffentlicht.

- `external_network` verbindet Traefik mit öffentlich erreichbaren Services.
- `internal_network` verbindet Traefik mit internen Services und privaten Backends. Den Zugriff auf interne Web-Routen begrenzt die Middleware `lan-only`; der Netzwerkname allein ist keine Zugriffssperre.
- Dienste mit benötigtem direktem Host-Zugriff können eigene Portfreigaben oder Host-Networking verwenden.

Traefik liest gemeinsame Middlewares und zusätzliche Router aus `config/traefik/dynamic/`. Das Verzeichnis ist als Ganzes eingebunden, damit Konfigurationsupdates sichtbar werden. `internal-app@file` bündelt LAN-Zugriffsschutz, Fehlerseiten und Security-Header.

Hostnamen werden über `.env` konfiguriert. Lokal sind `*.home.localhost` und `*.betz.localhost` vorgesehen, produktiv interne und externe Domains. Interne Zertifikate stellt Step CA über den Resolver `internalresolver` bereit. Für öffentliche Routen stehen Cloudflare-DNS-ACME über `externalresolver` und eine konfigurierbare Origin-Zertifikatsdatei zur Verfügung. Clients müssen der internen CA vertrauen.

## Lokaler Start

```bash
cp .env.local.example .env
mkdir -p secrets backups data/traefik/letsencrypt
chmod 700 secrets
printf 'dummy-local-token' > secrets/cloudflare_api_token
chmod 600 secrets/cloudflare_api_token

docker network create external_network || true
docker network create internal_network || true

docker compose --env-file .env --profile external config --quiet
docker compose up -d step-ca reverse-proxy homepage adguardhome
```

Die lokale Einstiegsseite ist unter `https://homepage.home.localhost` erreichbar. Weitere Hostnamen stehen in der gewählten Environment-Datei.

Optionale Services werden über Compose-Profile aktiviert: `external` für Cloudflare DDNS, `agent` für den Monitoring-Agent. Vor dem Start müssen die jeweiligen Zugangsdaten gesetzt sein.

## Produktion

Für eine neue Installation `.env.example` nach `.env` kopieren, die Werte anpassen und den Cloudflare-Token in `secrets/cloudflare_api_token` mit Dateimodus `600` ablegen. Die gemeinsamen Docker-Netzwerke müssen auch auf dem Server vorhanden sein. Persistente Daten liegen unter `/home/github/homelab/data`.

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

## Neue Services ergänzen

1. Compose-Datei unter `compose/apps/` oder `compose/core/` anlegen.
2. Datei in `compose.yaml` unter `include` eintragen.
3. Benötigte Variablen in `.env.example`, `.env.local.example` und der lokalen `.env` ergänzen.
4. Netzwerk, Traefik-Router, TLS und Zugriffsschutz festlegen; Daten unter `data/<service>/` ablegen.
5. Konfiguration prüfen:

```bash
docker compose --env-file .env --profile external config --quiet
```

Ein Beispiel bietet das [Service-Template](docs/service-template.md). Weitere Grundlagen: [Netzwerkisolation](docs/network-isolation.md), [Traefik-Access-Logs](docs/traefik-access-logs.md) und [Backup und Restore](docs/backup.md). Anwendungsspezifische Bedienung steht in den jeweiligen Runbooks unter `docs/`.
