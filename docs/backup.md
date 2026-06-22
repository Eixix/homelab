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

Update the existing host backup job to call:

```bash
/home/github/homelab/backup.sh
```

Use an S3 lifecycle policy for retention. Deep Archive is unsuitable for frequent restore drills, so periodically restore an archive into a temporary location and verify the encrypted archive checksum recorded in its S3 object metadata.

## Restore Outline

1. Restore and decrypt the archive into an empty `/home/github/homelab` directory.
2. Restore the database dumps with `mariadb` for Paperless/Shlink and `pg_restore` for Immich.
3. Start the stack with `docker compose --env-file .env --profile external up -d`.
4. Smoke-test each restored application before directing traffic to it.
