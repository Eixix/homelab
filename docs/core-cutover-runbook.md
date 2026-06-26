# Core Cutover Runbook

This is the first production handover from the old Portainer-managed core to the Git-managed Homelab stack. Run it only from an interactive shell on the production host.

## Preconditions

- GitHub Actions deploy has passed with an empty `services` input.
- `/home/github/homelab/.env` and `secrets/cloudflare_api_token` exist.
- Data has been pre-staged into `/home/github/homelab/data`.
- You are in a maintenance window: Traefik, AdGuard DNS, and Step CA will be restarted.

## Core Handover

```bash
sudo bash -euxo pipefail <<'EOF'
BASE=/home/github/homelab

sudo -u github bash -lc "cd '$BASE' && docker compose --env-file .env --profile external pull step-ca reverse-proxy adguardhome cloudflare-ddns"

for container in traefik cloudflare-ddns adguardhome step-ca; do
  if docker container inspect "${container}_legacy_git_cutover" >/dev/null 2>&1; then
    echo "Legacy cutover container already exists: ${container}_legacy_git_cutover" >&2
    exit 1
  fi
done

docker stop traefik cloudflare-ddns adguardhome step-ca

for container in traefik cloudflare-ddns adguardhome step-ca; do
  docker rename "$container" "${container}_legacy_git_cutover"
done

rsync -a /docker/step-ca/ "$BASE/data/step-ca/"
rsync -a /docker/letsencrypt/ "$BASE/data/traefik/letsencrypt/"
rsync -a /docker/adguardhome/work/ "$BASE/data/adguardhome/work/"
rsync -a /docker/adguardhome/conf/ "$BASE/data/adguardhome/conf/"
rsync -a /docker/certificates/cloudflare.crt "$BASE/data/traefik/certificates/cloudflare.crt"
rsync -a /docker/certificates/cloudflare.key "$BASE/data/traefik/certificates/cloudflare.key"

chown -R 1000:1000 "$BASE/data/step-ca"
chmod 600 "$BASE/data/traefik/certificates/cloudflare.key"

sudo -u github bash -lc "cd '$BASE' && docker compose --env-file .env --profile external up -d step-ca reverse-proxy adguardhome cloudflare-ddns"
EOF
```

## Immediate Checks

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'traefik|step-ca|adguardhome|cloudflare-ddns'
docker logs --tail=100 traefik
docker logs --tail=80 step-ca
docker logs --tail=80 adguardhome
```

From a LAN client, check:

- `https://traefik.home`
- `https://adguard.home`
- `https://homepage.home` after Homepage is started
- `https://dashboard.home` redirects to `https://homepage.home`

## Troubleshooting

- If `docker compose ... up` cannot resolve `registry-1.docker.io`, rollback or start old AdGuard again, then run the pull step before stopping DNS.
- If Step CA logs `defaults.json failed: permission denied`, restore the copied Step CA data ownership with `sudo chown -R 1000:1000 /home/github/homelab/data/step-ca` and recreate the container.

## Rollback

If the new core fails before apps are migrated:

```bash
sudo bash -euxo pipefail <<'EOF'
cd /home/github/homelab

docker compose --env-file .env --profile external rm -sf reverse-proxy adguardhome step-ca cloudflare-ddns || true

for container in traefik cloudflare-ddns adguardhome step-ca; do
  if docker container inspect "${container}_legacy_git_cutover" >/dev/null 2>&1; then
    docker rename "${container}_legacy_git_cutover" "$container"
  fi
done

docker start step-ca adguardhome traefik cloudflare-ddns
EOF
```
