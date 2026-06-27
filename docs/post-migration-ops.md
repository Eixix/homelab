# Post-Migration Operations

The homelab-owned stack is now Git-managed from `/home/github/homelab`. These are the remaining operational tasks that should happen after services have stayed stable for a bit.

## Restore Drill

Run one restore drill before treating the new backup path as authoritative. Use the detailed command in [Backups](./backup.md#restore-drill), but keep the drill isolated under `/tmp` and do not write over `/home/github/homelab`.

Minimum success criteria:

- The encrypted S3 object downloads successfully.
- The archive decrypts with `/etc/homelab-backup.passphrase`.
- The recorded object checksum matches the decrypted tarball.
- The archive extracts cleanly.
- `.env`, `compose.yaml`, and the Paperless, Shlink, and Immich database dumps are present.
- `docker compose --project-directory <restore-dir> --env-file <restore-dir>/.env --profile external config --quiet` passes.

Deep Archive restores can take time. Trigger the AWS restore first, then run the local verification once AWS reports the temporary restored object is available.

## Credential Rotation

Rotate credentials one class at a time, with a backup immediately before each change.

Recommended order:

1. Cloudflare API token in GitHub Actions and `/home/github/homelab/secrets/cloudflare_api_token`.
2. Beszel agent token/key, because old values may have been exposed during migration notes.
3. Shlink database credentials.
4. Paperless database/admin credentials.
5. Immich database credentials.

For Compose-managed services, update the GitHub `ENV_FILE` secret first, then deploy only the affected service set. Verify the app logs and login flow before rotating the next credential.

Do not commit real credentials to this repository. Keep `.env`, `/etc/homelab-backup.env`, GPG passphrases, API tokens, and webhook URLs only in server files or GitHub secrets.

## Step CA Decision

Keep the migrated Step CA data unless there is a deliberate reason to replace the internal trust root.

Regenerating Step CA means every client that trusts the current root CA needs to be re-enrolled or re-trusted. A cosmetic `STEP_CA_INIT_NAME` mismatch is not enough reason to do that. Only regenerate during a planned trust reset.

## Independent Projects

These projects intentionally stay outside this repo, but their deployment paths should be healthy:

- FollowUp: trigger the `Eixix/followup` deploy workflow so `/home/github/followup/dockerfiles/compose.yml` exists again.
- SplitLedger: identify the owning repo/deploy workflow and let that pipeline recreate `/home/github/splitledger/docker-compose.yml`.

Do not recreate those checkouts manually from this repo unless ownership changes and the services are explicitly moved into the homelab stack.

## n8n Task Runners

n8n is running, but logs showed the internal Python task runner cannot start because the main image lacks Python 3. Leave the current service alone unless workflows actually need Python Code node execution.

If Python execution is needed, add an external task runner sidecar with a dedicated shared runner token. Treat that as a small production change, not a cleanup item.
