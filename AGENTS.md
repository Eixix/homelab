# Agent Notes

This repository is public. Treat every real credential, token, webhook URL, `.env` value, and private key as secret. Do not commit local runtime files or copied production secrets.

## Workflow

- Prefer small, incremental changes and validate with `docker compose --env-file .env --profile external config --quiet`.
- Keep production deployment manual-only unless explicitly changed.
- Preserve `/home/github/homelab/.env`, `secrets/`, `data/`, and `backups/` during deployment.
- Ask before applying destructive production cleanup. Read-only SSH inspection is fine when needed for verification.

## Production Notes

- Production deploy path is `/home/github/homelab`.
- The Git-managed Traefik container is named `traefik`; Compose service name is `reverse-proxy`.
- Traefik dynamic config is mounted as a directory so rsync updates are visible to the running container.
- The repo backup is `/home/github/homelab/backup.sh` and is scheduled by `homelab-backup.timer`.
- The weekly storage backup job handles only the `/storage_array` S3 sync; Docker backups are scheduled separately by `homelab-backup.timer`.
- `/storage_array` ZFS findings are documented in `docs/storage-array-zfs.md`.

## Local Artifacts

Expected ignored local artifacts include:

- `.env`
- `secrets/cloudflare_api_token`
- `data/`
- `backups/`
- `backup-old.sh`
- `old-cron.sh`

Do not remove top-level `data/` unless the user explicitly asks and has confirmed it is safe.
