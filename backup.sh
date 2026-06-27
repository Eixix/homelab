#!/usr/bin/env bash
set -Eeuo pipefail

HOMELAB_ROOT="${HOMELAB_ROOT:-/home/github/homelab}"
BACKUP_CONFIG="${BACKUP_CONFIG:-/etc/homelab-backup.env}"
BACKUP_WORK_DIR="${BACKUP_WORK_DIR:-/tmp}"

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'Missing required command: %s\n' "$1" >&2
    exit 1
  }
}

for command in aws docker gpg sha256sum tar; do
  require_command "$command"
done

[[ -r "$BACKUP_CONFIG" ]] || {
  printf 'Backup configuration is not readable: %s\n' "$BACKUP_CONFIG" >&2
  exit 1
}
[[ -r "$HOMELAB_ROOT/.env" ]] || {
  printf 'Production environment file is not readable: %s/.env\n' "$HOMELAB_ROOT" >&2
  exit 1
}

# shellcheck disable=SC1090
source "$BACKUP_CONFIG"
: "${S3_BUCKET:?Set S3_BUCKET in the backup configuration}"
: "${GPG_PASSPHRASE_FILE:?Set GPG_PASSPHRASE_FILE in the backup configuration}"
[[ -r "$GPG_PASSPHRASE_FILE" ]] || {
  printf 'GPG passphrase file is not readable: %s\n' "$GPG_PASSPHRASE_FILE" >&2
  exit 1
}

# Compose secrets are sourced only to create consistent database dumps.
set -a
# shellcheck disable=SC1090
source "$HOMELAB_ROOT/.env"
set +a

BACKUP_ID="$(hostname -s)-$(date -u +%Y%m%dT%H%M%SZ)"
STAGING_DIR="$(mktemp -d "$BACKUP_WORK_DIR/homelab-backup.XXXXXX")"
ARCHIVE="$STAGING_DIR/$BACKUP_ID.tar.gz"
ENCRYPTED_ARCHIVE="$ARCHIVE.gpg"
LOG_DIR="$HOMELAB_ROOT/backups/logs"
LOG_FILE="$LOG_DIR/$BACKUP_ID.log"

cleanup() {
  rm -rf "$STAGING_DIR"
}
trap cleanup EXIT

mkdir -p "$LOG_DIR" "$STAGING_DIR/database"
exec > >(tee -a "$LOG_FILE") 2>&1

printf '%s Starting backup %s\n' "$(date -u +%FT%TZ)" "$BACKUP_ID"

docker exec -e MARIADB_PWD="$PAPERLESS_DB_ROOT_PASSWORD" paperless-db \
  mariadb-dump --user=root --single-transaction --routines --events --databases paperless \
  > "$STAGING_DIR/database/paperless.sql"

docker exec -e MARIADB_PWD="$SHLINK_DB_ROOT_PASSWORD" shlink-database \
  mariadb-dump --user=root --single-transaction --routines --events --databases shlink \
  > "$STAGING_DIR/database/shlink.sql"

docker exec -e PGPASSWORD="$IMMICH_DB_PASSWORD" immich_postgres \
  pg_dump --username="$IMMICH_DB_USERNAME" --format=custom "$IMMICH_DB_DATABASE_NAME" \
  > "$STAGING_DIR/database/immich.dump"

for dump in "$STAGING_DIR"/database/*; do
  [[ -s "$dump" ]] || {
    printf 'Database dump is empty: %s\n' "$dump" >&2
    exit 1
  }
done

tar --create --gzip --file "$ARCHIVE" \
  --directory "$HOMELAB_ROOT" \
  --exclude='data/immich/database' \
  --exclude='data/paperless/db' \
  --exclude='data/shlink/db' \
  .env .env.example .github backup.sh compose.yaml compose config data docs README.md secrets \
  --directory "$STAGING_DIR" database

ARCHIVE_SHA256="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
gpg --batch --yes --pinentry-mode loopback \
  --passphrase-file "$GPG_PASSPHRASE_FILE" \
  --symmetric --cipher-algo AES256 \
  --output "$ENCRYPTED_ARCHIVE" "$ARCHIVE"

aws s3 cp "$ENCRYPTED_ARCHIVE" "$S3_BUCKET/${S3_PREFIX:-homelab}/$BACKUP_ID.tar.gz.gpg" \
  --storage-class "${AWS_STORAGE_CLASS:-DEEP_ARCHIVE}" \
  --metadata "sha256=$ARCHIVE_SHA256"

printf '%s Backup completed: %s\n' "$(date -u +%FT%TZ)" "$BACKUP_ID"
