# App Cutover Runbook

Use this after the Git-managed core stack is healthy. Migrate one app at a time.

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
