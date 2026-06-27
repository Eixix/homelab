# Backups

The production backup script is [`backup.sh`](../backup.sh). It backs up the repository-managed state under `/home/github/homelab`, including `data/`, `config/`, `secrets/`, and `.env`. It makes logical dumps of the Paperless, Shlink, and Immich databases instead of archiving live database files.

`/storage_array` is intentionally not part of this script. Keep its existing S3 sync job as the separate backup path for Immich photos, media, libraries, and Paperless consumption.

## Production Setup

Create `/etc/homelab-backup.env` with mode `600`:

```bash
S3_BUCKET=s3://docker-compose-backup
S3_PREFIX=homelab
AWS_STORAGE_CLASS=DEEP_ARCHIVE
GPG_PASSPHRASE_FILE=/etc/homelab-backup.passphrase
```

Store the GPG passphrase in `/etc/homelab-backup.passphrase` with mode `600`. AWS credentials remain configured for the account that runs the job.

The host needs `aws`, `docker`, `gpg`, `sha256sum`, and `tar`. Database dump clients do not need to be installed on the host because `backup.sh` runs `mariadb-dump` and `pg_dump` inside the running database containers.

Example setup:

```bash
sudo bash -euxo pipefail <<'EOF'
install -m 600 -o root -g root /dev/null /etc/homelab-backup.env
cat >/etc/homelab-backup.env <<'ENV'
S3_BUCKET=s3://REPLACE_ME
S3_PREFIX=homelab
AWS_STORAGE_CLASS=DEEP_ARCHIVE
GPG_PASSPHRASE_FILE=/etc/homelab-backup.passphrase
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

## Replacing the Old Docker Backup

The old production Docker backup entry point is `/docker-compose-services/backup-script.sh`. It belongs to the pre-migration bind-mount layout and should not remain the authoritative Docker backup after the Git-managed stack is verified.

Keep the existing outer storage-array backup job, including its notification webhook and `/storage_array` S3 sync, but replace only the Docker backup call:

```diff
- /docker-compose-services/backup-script.sh
+ /home/github/homelab/backup.sh
```

After one successful encrypted homelab backup and one restore drill, archive or remove `/docker-compose-services/backup-script.sh` as part of the production server cleanup.

Use an S3 lifecycle policy for retention. Deep Archive is unsuitable for frequent restore drills, so periodically restore an archive into a temporary location and verify the encrypted archive checksum recorded in its S3 object metadata.

## Restore Outline

1. Restore and decrypt the archive into an empty `/home/github/homelab` directory.
2. Restore the database dumps with `mariadb` for Paperless/Shlink and `pg_restore` for Immich.
3. Start the stack with `docker compose --env-file .env --profile external up -d`.
4. Smoke-test each restored application before directing traffic to it.
