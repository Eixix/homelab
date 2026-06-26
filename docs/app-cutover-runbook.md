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
