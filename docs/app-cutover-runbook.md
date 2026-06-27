# App Cutover Runbook

Use this after the Git-managed core stack is healthy. Migrate one app at a time.

## Shared Host Settings

Redis-backed services such as Paperless and Immich expect Linux memory overcommit to be enabled. Configure this once on the production host:

```bash
sudo bash -euxo pipefail <<'EOF'
printf 'vm.overcommit_memory = 1\n' >/etc/sysctl.d/99-homelab-redis.conf
sysctl --system
EOF
```

Verify:

```bash
cat /proc/sys/vm/overcommit_memory
```

The expected value is `1`.

## Homepage

Homepage is the first app cutover because it has no database state. The old container is named `homepage` and was created by the old Portainer stack, so its name must be freed before the Git-managed Compose service can start.

### Handover

Run on the production host:

```bash
sudo bash -euxo pipefail <<'EOF'
if docker container inspect homepage_legacy_git_cutover >/dev/null 2>&1; then
  echo "homepage_legacy_git_cutover already exists" >&2
  exit 1
fi

docker stop homepage
docker rename homepage homepage_legacy_git_cutover
EOF
```

Then run the GitHub Actions deploy workflow with:

```text
services = homepage
```

### Checks

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep homepage
docker logs --tail=80 homepage
```

From a LAN client:

- `https://homepage.home`
- `https://dashboard.home` redirects to `https://homepage.home`

### Rollback

```bash
sudo bash -euxo pipefail <<'EOF'
cd /home/github/homelab
docker compose --env-file .env --profile external rm -sf homepage || true

if docker container inspect homepage_legacy_git_cutover >/dev/null 2>&1; then
  docker rename homepage_legacy_git_cutover homepage
fi

docker start homepage
EOF
```

## Legacy Wedding

Wedding is excluded from this repository migration because it is owned by a separate GitHub deployment. The old containers still had Traefik labels, which made the new Traefik try to issue unsupported `tobiasbetz.de` certificates.

### Disable Legacy Ingress

Run on the production host:

```bash
sudo bash -euxo pipefail <<'EOF'
for container in wedding_frontend wedding_backend; do
  if docker container inspect "${container}_legacy_git_cutover" >/dev/null 2>&1; then
    echo "${container}_legacy_git_cutover already exists" >&2
    exit 1
  fi
done

docker stop wedding_frontend wedding_backend
docker rename wedding_frontend wedding_frontend_legacy_git_cutover
docker rename wedding_backend wedding_backend_legacy_git_cutover
EOF
```

### Rollback

```bash
sudo bash -euxo pipefail <<'EOF'
for container in wedding_frontend wedding_backend; do
  if docker container inspect "${container}_legacy_git_cutover" >/dev/null 2>&1; then
    docker rename "${container}_legacy_git_cutover" "$container"
  fi
done

docker start wedding_frontend wedding_backend
EOF
```

## Vaultwarden

Vaultwarden uses SQLite under `/data`, so stop the old container before the final sync.

### Handover

Run on the production host:

```bash
sudo bash -euxo pipefail <<'EOF'
BASE=/home/github/homelab

if docker container inspect vaultwarden_legacy_git_cutover >/dev/null 2>&1; then
  echo "vaultwarden_legacy_git_cutover already exists" >&2
  exit 1
fi

docker stop vaultwarden
docker rename vaultwarden vaultwarden_legacy_git_cutover

install -d -o github -g github "$BASE/data/vaultwarden"
rsync -a --delete /docker-compose-services/vaultwarden/ "$BASE/data/vaultwarden/"
chown -R github:github "$BASE/data/vaultwarden"
EOF
```

Then run the GitHub Actions deploy workflow with:

```text
services = vaultwarden
```

### Checks

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep vaultwarden
docker logs --tail=80 vaultwarden
```

From a client:

- `https://passwort.betz.coffee`
- Browser extension/mobile sync
- Admin page policy, if the production config enables it

### Rollback

```bash
sudo bash -euxo pipefail <<'EOF'
cd /home/github/homelab
docker compose --env-file .env --profile external rm -sf vaultwarden || true

if docker container inspect vaultwarden_legacy_git_cutover >/dev/null 2>&1; then
  docker rename vaultwarden_legacy_git_cutover vaultwarden
fi

docker start vaultwarden
EOF
```

## Shlink

Shlink uses a MariaDB data directory. Stop the old API, web client, and database before the final sync. The existing API used the MariaDB `root` account, so the Git-managed service intentionally connects with `SHLINK_DB_ROOT_PASSWORD` during this migration.

### Handover

Run on the production host:

```bash
sudo bash -euxo pipefail <<'EOF'
BASE=/home/github/homelab

for container in shlink shlink-web shlink_database; do
  if docker container inspect "${container}_legacy_git_cutover" >/dev/null 2>&1; then
    echo "${container}_legacy_git_cutover already exists" >&2
    exit 1
  fi
done

docker stop shlink shlink-web shlink_database
docker rename shlink shlink_legacy_git_cutover
docker rename shlink-web shlink-web_legacy_git_cutover
docker rename shlink_database shlink_database_legacy_git_cutover

install -d "$BASE/data/shlink/db"
rsync -a --delete /docker-compose-services/shlink/db_data/ "$BASE/data/shlink/db/"
chown -R 999:999 "$BASE/data/shlink/db"
EOF
```

Then run the GitHub Actions deploy workflow with:

```text
services = shlink-database shlink shlink-web
```

### Checks

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'shlink|shlink-database'
docker logs --tail=80 shlink-database
docker logs --tail=80 shlink
docker logs --tail=80 shlink-web
```

From a client:

- `https://l.betz.coffee`
- `https://shlink.home`
- Create or verify the API key used by the web client.

### Rollback

```bash
sudo bash -euxo pipefail <<'EOF'
cd /home/github/homelab
docker compose --env-file .env --profile external rm -sf shlink shlink-web shlink-database || true

for container in shlink shlink-web shlink_database; do
  if docker container inspect "${container}_legacy_git_cutover" >/dev/null 2>&1; then
    docker rename "${container}_legacy_git_cutover" "$container"
  fi
done

docker start shlink_database shlink shlink-web
EOF
```

## Actual Budget

Actual Budget stores its state under `/data`. Stop the old container before the final sync.

### Handover

Run on the production host:

```bash
sudo bash -euxo pipefail <<'EOF'
BASE=/home/github/homelab

if docker container inspect actual-server_legacy_git_cutover >/dev/null 2>&1; then
  echo "actual-server_legacy_git_cutover already exists" >&2
  exit 1
fi

docker stop actual-server
docker rename actual-server actual-server_legacy_git_cutover

install -d "$BASE/data/actual"
rsync -a --delete /docker-compose-services/actual/data/ "$BASE/data/actual/"
EOF
```

Then run the GitHub Actions deploy workflow with:

```text
services = actual-server
```

### Checks

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep actual-server
docker logs --tail=80 actual-server
```

From a LAN client:

- `https://budget.home`

### Rollback

```bash
sudo bash -euxo pipefail <<'EOF'
cd /home/github/homelab
docker compose --env-file .env --profile external rm -sf actual-server || true

if docker container inspect actual-server_legacy_git_cutover >/dev/null 2>&1; then
  docker rename actual-server_legacy_git_cutover actual-server
fi

docker start actual-server
EOF
```

## go2rtc

go2rtc stores its configuration under `/config`. The old and Git-managed containers both run privileged.

### Handover

Run on the production host:

```bash
sudo bash -euxo pipefail <<'EOF'
BASE=/home/github/homelab

if docker container inspect go2rtc_legacy_git_cutover >/dev/null 2>&1; then
  echo "go2rtc_legacy_git_cutover already exists" >&2
  exit 1
fi

docker stop go2rtc
docker rename go2rtc go2rtc_legacy_git_cutover

install -d "$BASE/data/go2rtc"
rsync -a --delete /docker-compose-services/go2rtc/ "$BASE/data/go2rtc/"
EOF
```

Then run the GitHub Actions deploy workflow with:

```text
services = go2rtc
```

### Checks

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep go2rtc
docker logs --tail=80 go2rtc
```

From a LAN client:

- `https://go2rtc.home`
- Camera streams used by Home Assistant

### Rollback

```bash
sudo bash -euxo pipefail <<'EOF'
cd /home/github/homelab
docker compose --env-file .env --profile external rm -sf go2rtc || true

if docker container inspect go2rtc_legacy_git_cutover >/dev/null 2>&1; then
  docker rename go2rtc_legacy_git_cutover go2rtc
fi

docker start go2rtc
EOF
```

## KitchenOwl

KitchenOwl uses a frontend/backend pair. The backend stores SQLite data and uploads under `/data`, so stop both old containers before the final sync.

### Handover

Run on the production host:

```bash
sudo bash -euxo pipefail <<'EOF'
BASE=/home/github/homelab

for container in kitchenowlfront kitchenowlback; do
  if docker container inspect "${container}_legacy_git_cutover" >/dev/null 2>&1; then
    echo "${container}_legacy_git_cutover already exists" >&2
    exit 1
  fi
done

docker stop kitchenowlfront kitchenowlback
docker rename kitchenowlfront kitchenowlfront_legacy_git_cutover
docker rename kitchenowlback kitchenowlback_legacy_git_cutover

install -d "$BASE/data/kitchenowl"
rsync -a --delete /docker-compose-services/kitchenowl-data/ "$BASE/data/kitchenowl/"
EOF
```

Then run the GitHub Actions deploy workflow with:

```text
services = kitchenowl-back kitchenowl-front
```

### Checks

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep kitchenowl
docker logs --tail=80 kitchenowlback
docker logs --tail=80 kitchenowlfront
```

From a client:

- `https://shopping.betz.coffee`
- Login and frontend/backend API flow

### Rollback

```bash
sudo bash -euxo pipefail <<'EOF'
cd /home/github/homelab
docker compose --env-file .env --profile external rm -sf kitchenowl-front kitchenowl-back || true

for container in kitchenowlfront kitchenowlback; do
  if docker container inspect "${container}_legacy_git_cutover" >/dev/null 2>&1; then
    docker rename "${container}_legacy_git_cutover" "$container"
  fi
done

docker start kitchenowlback kitchenowlfront
EOF
```

## n8n

n8n uses SQLite and stores credentials/workflows under `/home/node/.n8n`. Stop the old container before the final sync. The Git-managed service no longer publishes host port `5678`; access goes through Traefik at `https://n8n.home`.

### Handover

Run on the production host:

```bash
sudo bash -euxo pipefail <<'EOF'
BASE=/home/github/homelab

if docker container inspect n8n_legacy_git_cutover >/dev/null 2>&1; then
  echo "n8n_legacy_git_cutover already exists" >&2
  exit 1
fi

docker stop n8n
docker rename n8n n8n_legacy_git_cutover

install -d "$BASE/data/n8n"
rsync -a --delete /docker-compose-services/n8n/ "$BASE/data/n8n/"
chown -R github:github "$BASE/data/n8n"
EOF
```

The Git-managed n8n service runs as the deploy user. It sets `N8N_USER_FOLDER=/home/node` so n8n uses the mounted default data directory at `/home/node/.n8n`, bind-mounts `data/n8n/.cache` to `/home/node/.cache` because n8n's startup asset generation writes there even when `XDG_CACHE_HOME` points elsewhere, and sets `N8N_PROXY_HOPS=1` for the Traefik hop in front of n8n.

Then run the GitHub Actions deploy workflow with:

```text
services = n8n
```

If an earlier failed start created a nested fresh database at `data/n8n/.n8n`, move it aside before recreating the service:

```bash
sudo bash -euxo pipefail <<'EOF'
BASE=/home/github/homelab
TS=$(date +%Y%m%d-%H%M%S)
docker compose --env-file "$BASE/.env" --profile external stop n8n || true
if [ -d "$BASE/data/n8n/.n8n" ]; then
  mv "$BASE/data/n8n/.n8n" "$BASE/data/n8n/.n8n.empty-$TS"
fi
EOF
```

### Checks

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep n8n
docker logs --tail=120 n8n
```

From a LAN client:

- `https://n8n.home`
- Editor loads existing workflows.
- Webhook/test webhook URLs use `https://n8n.home`.
- If workflows need Python Code node execution, add an external task runner sidecar with a shared `N8N_RUNNERS_AUTH_TOKEN`. Current production logs show the internal Python task runner cannot start because Python 3 is not present in the main n8n image, and n8n recommends external runners for production.

### Rollback

```bash
sudo bash -euxo pipefail <<'EOF'
cd /home/github/homelab
docker compose --env-file .env --profile external rm -sf n8n || true

if docker container inspect n8n_legacy_git_cutover >/dev/null 2>&1; then
  docker rename n8n_legacy_git_cutover n8n
fi

docker start n8n
EOF
```

## Kavita

Kavita stores its application config, database, covers, progress, and cache under `/kavita/config`. Stop the old container before the final sync. The book and comic libraries stay on `/storage_array` and are mounted read-only by the Git-managed service.

### Handover

Run on the production host:

```bash
sudo bash -euxo pipefail <<'EOF'
BASE=/home/github/homelab

if docker container inspect kavita_legacy_git_cutover >/dev/null 2>&1; then
  echo "kavita_legacy_git_cutover already exists" >&2
  exit 1
fi

docker stop kavita
docker rename kavita kavita_legacy_git_cutover

install -d "$BASE/data/kavita/config"
rsync -a --delete /docker-compose-services/kavita/data/ "$BASE/data/kavita/config/"
EOF
```

Then run the GitHub Actions deploy workflow with:

```text
services = kavita
```

### Checks

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep kavita
docker logs --tail=100 kavita
```

From a LAN client:

- `https://reader.home`
- Existing users, libraries, reading progress, and covers are present.
- Books and comics library scans can read `/books` and `/comics`.

### Rollback

```bash
sudo bash -euxo pipefail <<'EOF'
cd /home/github/homelab
docker compose --env-file .env --profile external rm -sf kavita || true

if docker container inspect kavita_legacy_git_cutover >/dev/null 2>&1; then
  docker rename kavita_legacy_git_cutover kavita
fi

docker start kavita
EOF
```

## Home Assistant

Home Assistant stores its config, `.storage` auth state, recorder database, custom components, secrets, and local tokens under `/config`. Stop the old container before the final sync. The Git-managed service intentionally keeps `network_mode: host`, `privileged: true`, `/run/dbus`, and `/etc/localtime` to match the existing production container.

Before cutover, verify `/docker-compose-services/homeassistant/configuration.yaml` includes `http.use_x_forwarded_for: true` and a `trusted_proxies` range that covers Traefik's Docker source address.

### Handover

Run on the production host:

```bash
sudo bash -euxo pipefail <<'EOF'
BASE=/home/github/homelab

if docker container inspect homeassistant_legacy_git_cutover >/dev/null 2>&1; then
  echo "homeassistant_legacy_git_cutover already exists" >&2
  exit 1
fi

docker stop homeassistant
docker rename homeassistant homeassistant_legacy_git_cutover

install -d "$BASE/data/homeassistant"
rsync -a --delete /docker-compose-services/homeassistant/ "$BASE/data/homeassistant/"
EOF
```

Then run the GitHub Actions deploy workflow with:

```text
services = homeassistant
```

### Checks

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep homeassistant
docker logs --tail=160 homeassistant
```

From a LAN client:

- `https://hass.home`
- Existing users, roles, MFA settings, integrations, and dashboards are present.
- Long-lived tokens and mobile app sessions still work.
- Actual Alexa/auth flow still reaches `https://hass.betz.coffee/auth` and `/api/alexa`.

### Rollback

```bash
sudo bash -euxo pipefail <<'EOF'
cd /home/github/homelab
docker compose --env-file .env --profile external rm -sf homeassistant || true

if docker container inspect homeassistant_legacy_git_cutover >/dev/null 2>&1; then
  docker rename homeassistant_legacy_git_cutover homeassistant
fi

docker start homeassistant
EOF
```

## Paperless-ngx

Paperless uses MariaDB, Redis, and filesystem data/media/export directories. Stop the old web, database, and broker containers before the final sync. The consume directory stays on `/storage_array/documents`.

Before cutover, confirm the production `.env` contains real values for `PAPERLESS_DB_PASSWORD`, `PAPERLESS_DB_ROOT_PASSWORD`, `PAPERLESS_SECRET_KEY`, `PAPERLESS_ADMIN_USER`, and `PAPERLESS_ADMIN_PASSWORD`. The old Outlook OAuth integration is intentionally not migrated.

### Handover

Run on the production host:

```bash
sudo bash -euxo pipefail <<'EOF'
BASE=/home/github/homelab

for container in paperless-paperless-web-1 paperless-paperless-db-1 paperless-paperless-broker-1; do
  legacy="${container}_legacy_git_cutover"
  if docker container inspect "$legacy" >/dev/null 2>&1; then
    echo "$legacy already exists" >&2
    exit 1
  fi
done

docker stop paperless-paperless-web-1 paperless-paperless-db-1 paperless-paperless-broker-1
docker rename paperless-paperless-web-1 paperless-paperless-web-1_legacy_git_cutover
docker rename paperless-paperless-db-1 paperless-paperless-db-1_legacy_git_cutover
docker rename paperless-paperless-broker-1 paperless-paperless-broker-1_legacy_git_cutover

install -d "$BASE/data/paperless/db" "$BASE/data/paperless/redis" "$BASE/data/paperless/data" "$BASE/data/paperless/media" "$BASE/data/paperless/export"
rsync -a --delete /docker-compose-services/paperless-db/ "$BASE/data/paperless/db/"
rsync -a --delete /docker-compose-services/paperless-redis/ "$BASE/data/paperless/redis/"
rsync -a --delete /docker-compose-services/paperless-data/ "$BASE/data/paperless/data/"
rsync -a --delete /docker-compose-services/paperless-media/ "$BASE/data/paperless/media/"
rsync -a --delete /docker-compose-services/paperless-export/ "$BASE/data/paperless/export/"

chown -R 999:999 "$BASE/data/paperless/db"
EOF
```

Then run the GitHub Actions deploy workflow with:

```text
services = paperless-broker paperless-db paperless-web
```

### Checks

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep paperless
docker logs --tail=120 paperless-db
docker logs --tail=120 paperless-broker
docker logs --tail=160 paperless-web
```

From a LAN client:

- `https://dokumente.home`
- Existing users, documents, tags, correspondents, storage paths, and thumbnails are present.
- The consume mount points at `/storage_array/documents`.
- Outlook OAuth import is absent by design.

### Rollback

```bash
sudo bash -euxo pipefail <<'EOF'
cd /home/github/homelab
docker compose --env-file .env --profile external rm -sf paperless-web paperless-db paperless-broker || true

for container in paperless-paperless-broker-1 paperless-paperless-db-1 paperless-paperless-web-1; do
  if docker container inspect "${container}_legacy_git_cutover" >/dev/null 2>&1; then
    docker rename "${container}_legacy_git_cutover" "$container"
  fi
done

docker start paperless-paperless-broker-1 paperless-paperless-db-1 paperless-paperless-web-1
EOF
```

## Immich

Immich uses Postgres, Redis, machine learning cache, and the photo library under `/storage_array/Photos`. Stop all old Immich containers before the final database sync. The upload/photo library is not copied into `data/`; it remains mounted from `/storage_array/Photos` and is backed up by the storage-array job.

The existing production database currently depends on the existing Immich DB credentials. Preserve them for this cutover and rotate later as a separate maintenance task. The old `/docker-compose-services/immich/typesense` directory is not mounted by the current Immich stack.

### Handover

Run on the production host:

```bash
sudo bash -euxo pipefail <<'EOF'
BASE=/home/github/homelab

for container in immich_server immich_machine_learning immich_postgres immich_redis; do
  if docker container inspect "${container}_legacy_git_cutover" >/dev/null 2>&1; then
    echo "${container}_legacy_git_cutover already exists" >&2
    exit 1
  fi
done

docker stop immich_server immich_machine_learning immich_postgres immich_redis
docker rename immich_server immich_server_legacy_git_cutover
docker rename immich_machine_learning immich_machine_learning_legacy_git_cutover
docker rename immich_postgres immich_postgres_legacy_git_cutover
docker rename immich_redis immich_redis_legacy_git_cutover

install -d "$BASE/data/immich/database" "$BASE/data/immich/model-cache"
rsync -a --delete /docker-compose-services/immich/database/ "$BASE/data/immich/database/"
rsync -a --delete /docker-compose-services/immich/model-cache/ "$BASE/data/immich/model-cache/"
chown -R 999:0 "$BASE/data/immich/database"
EOF
```

Then run the GitHub Actions deploy workflow with:

```text
services = immich-redis immich-postgres immich-machine-learning immich-server
```

### Checks

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep immich
docker logs --tail=120 immich_postgres
docker logs --tail=120 immich_redis
docker logs --tail=120 immich_machine_learning
docker logs --tail=180 immich_server
```

From a client:

- `https://fotos.home`
- `https://fotos.betz.coffee`
- `https://fotos.fabian-und-kristina.de`
- Existing users, albums, assets, thumbnails, and mobile app access are present.
- Upload mount points at `/storage_array/Photos`.

### Rollback

```bash
sudo bash -euxo pipefail <<'EOF'
cd /home/github/homelab
docker compose --env-file .env --profile external rm -sf immich-server immich-machine-learning immich-postgres immich-redis || true

for container in immich_redis immich_postgres immich_machine_learning immich_server; do
  if docker container inspect "${container}_legacy_git_cutover" >/dev/null 2>&1; then
    docker rename "${container}_legacy_git_cutover" "$container"
  fi
done

docker start immich_redis immich_postgres immich_machine_learning immich_server
EOF
```

## Beszel

Beszel stores hub data in `/beszel_data`, socket state in `/beszel_socket`, and the local agent fingerprint under `/var/lib/beszel-agent`. Stop both old containers before the final sync. The agent keeps host networking, read-only Docker socket access, and the extra filesystem mount at `/storage_array/.beszel`.

Before cutover, confirm the production `.env` contains the real `BESZEL_AGENT_KEY` and `BESZEL_AGENT_TOKEN` values. They are sensitive and should be rotated later because earlier examples may have exposed old values.

### Handover

Run on the production host:

```bash
sudo bash -euxo pipefail <<'EOF'
BASE=/home/github/homelab

for container in beszel beszel-agent; do
  if docker container inspect "${container}_legacy_git_cutover" >/dev/null 2>&1; then
    echo "${container}_legacy_git_cutover already exists" >&2
    exit 1
  fi
done

docker stop beszel-agent beszel
docker rename beszel beszel_legacy_git_cutover
docker rename beszel-agent beszel-agent_legacy_git_cutover

install -d "$BASE/data/monitoring/beszel/data" "$BASE/data/monitoring/beszel/socket" "$BASE/data/monitoring/beszel-agent"
rsync -a --delete /docker-compose-services/beszel_data/ "$BASE/data/monitoring/beszel/data/"
rsync -a --delete /docker-compose-services/beszel_socket/ "$BASE/data/monitoring/beszel/socket/"
rsync -a --delete /data/compose/7/beszel_agent_data/ "$BASE/data/monitoring/beszel-agent/"
EOF
```

Then run the GitHub Actions deploy workflow with:

```text
services = beszel beszel-agent
```

### Checks

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep beszel
docker logs --tail=120 beszel
docker logs --tail=120 beszel-agent
```

From a LAN client:

- `https://beszel.home`
- Existing hub login and monitored host data are present.
- The agent reports Docker and `/storage_array/.beszel` filesystem data.

### Rollback

```bash
sudo bash -euxo pipefail <<'EOF'
cd /home/github/homelab
docker compose --env-file .env --profile external --profile agent rm -sf beszel beszel-agent || true

for container in beszel beszel-agent; do
  if docker container inspect "${container}_legacy_git_cutover" >/dev/null 2>&1; then
    docker rename "${container}_legacy_git_cutover" "$container"
  fi
done

docker start beszel beszel-agent
EOF
```
