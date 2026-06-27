# Backups

The production backup script is [`backup.sh`](../backup.sh). It backs up the repository-managed state under `/home/github/homelab`, including Compose files, `config/`, `data/`, `docs/`, `secrets/`, `.env`, and the backup script itself. It makes logical dumps of the Paperless, Shlink, and Immich databases instead of archiving live database files.

`/storage_array` is intentionally not part of this script. Keep its existing S3 sync job as the separate backup path for Immich photos, media, libraries, and Paperless consumption.

Home Assistant recorder history files (`home-assistant_v2.db*`), runtime locks, and logs are excluded because they change continuously while Home Assistant is running. Home Assistant config, `.storage`, auth state, and YAML files remain in the archive.

## Production Setup

Create `/etc/homelab-backup.env` with mode `600`:

```bash
S3_BUCKET=s3://docker-compose-backup
S3_PREFIX=homelab
AWS_STORAGE_CLASS=DEEP_ARCHIVE
GPG_PASSPHRASE_FILE=/etc/homelab-backup.passphrase
N8N_WEBHOOK=https://n8n.home/webhook/REPLACE_ME
```

Store the GPG passphrase in `/etc/homelab-backup.passphrase` with mode `600`. AWS credentials remain configured for the account that runs the job. `N8N_WEBHOOK` is optional; when set, `backup.sh` posts success and failure notifications itself.

The host needs `aws`, `docker`, `gpg`, `sha256sum`, and `tar`. Database dump clients do not need to be installed on the host because `backup.sh` runs `mariadb-dump` and `pg_dump` inside the running database containers. The Compose `.env` file is not shell-sourced; values such as `STEP_CA_INIT_NAME=Homelab Internal CA` can stay in Compose dotenv format.

Example setup:

```bash
sudo bash -euxo pipefail <<'EOF'
install -m 600 -o root -g root /dev/null /etc/homelab-backup.env
cat >/etc/homelab-backup.env <<'ENV'
S3_BUCKET=s3://REPLACE_ME
S3_PREFIX=homelab
AWS_STORAGE_CLASS=DEEP_ARCHIVE
GPG_PASSPHRASE_FILE=/etc/homelab-backup.passphrase
# Optional:
# N8N_WEBHOOK=https://n8n.home/webhook/REPLACE_ME
ENV

install -m 600 -o root -g root /dev/null /etc/homelab-backup.passphrase
openssl rand -base64 48 >/etc/homelab-backup.passphrase
EOF
```

Update the existing host backup job to call:

```bash
/home/github/homelab/backup.sh
```

Run the job as a user that can read `/home/github/homelab`, `/etc/homelab-backup.env`, and `/etc/homelab-backup.passphrase`, and can access Docker plus AWS credentials. Root is the simplest fit for the current production layout because `/home/github` is not world-readable.

## Periodic Schedule

Use a systemd timer for the repo-managed homelab backup. This keeps the Docker/app backup independent from the separate `/storage_array` S3 sync and gives a clear status surface with `systemctl`.

Example weekly Sunday 23:00 setup:

```bash
sudo bash -euxo pipefail <<'EOF'
cat >/etc/systemd/system/homelab-backup.service <<'SERVICE'
[Unit]
Description=Homelab encrypted Docker/app backup
Wants=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
ExecStart=/home/github/homelab/backup.sh
SERVICE

cat >/etc/systemd/system/homelab-backup.timer <<'TIMER'
[Unit]
Description=Run Homelab encrypted Docker/app backup weekly

[Timer]
OnCalendar=Sun *-*-* 23:00:00
Persistent=true
RandomizedDelaySec=10m

[Install]
WantedBy=timers.target
TIMER

systemctl daemon-reload
systemctl enable --now homelab-backup.timer
systemctl list-timers homelab-backup.timer --no-pager
EOF
```

Manual status checks:

```bash
sudo systemctl status homelab-backup.timer
sudo systemctl status homelab-backup.service
sudo journalctl -u homelab-backup.service -n 120 --no-pager
```

## Replacing the Old Docker Backup

The old production Docker backup entry point is `/docker-compose-services/backup-script.sh`. It belongs to the pre-migration bind-mount layout and should not remain the authoritative Docker backup after the Git-managed stack is verified. Keep it untouched until the new encrypted backup has succeeded and a restore drill has proven the archive.

Keep the existing outer storage-array backup job, including its notification webhook and `/storage_array` S3 sync, but replace only the Docker backup call:

```diff
- /docker-compose-services/backup-script.sh
+ /home/github/homelab/backup.sh
```

After one successful encrypted homelab backup and one restore drill, archive or remove `/docker-compose-services/backup-script.sh` as part of the production server cleanup.

If you keep the existing wrapper shape, its Docker-backup section can either keep wrapping notifications or simply call the repo script. When `N8N_WEBHOOK` is set in `/etc/homelab-backup.env`, this is enough:

```sh
####################################
# Homelab Docker backup
####################################
/home/github/homelab/backup.sh
```

Keep the existing `/storage_array` S3 sync section after this block.

Use an S3 lifecycle policy for retention. Deep Archive is unsuitable for frequent restore drills, so periodically restore an archive into a temporary location and verify the encrypted archive checksum recorded in its S3 object metadata.

## Restore Outline

1. Restore and decrypt the archive into an empty `/home/github/homelab` directory.
2. Restore the database dumps with `mariadb` for Paperless/Shlink and `pg_restore` for Immich.
3. Start the stack with `docker compose --env-file .env --profile external up -d`.
4. Smoke-test each restored application before directing traffic to it.
