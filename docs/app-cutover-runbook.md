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
