# Digital Legacy

This page explains what matters in an emergency and where the relevant information lives. It intentionally does not contain passwords, tokens, private keys, or personal credentials.

## Goal

If Tobias is unavailable or cannot take care of the homelab himself, operations should not fail because context is missing.

The main goals are:

- make important passwords available through Bitwarden Emergency Access
- involve Michael or Fabian for technical support
- make the existing documentation easy to find
- avoid rushed changes on the server

## Who Can Help Technically?

Michael or Fabian can help with technical tasks in an emergency.

One of them can access the server with the YubiKey. The YubiKey is a physical security key. It adds protection so server access does not depend on a password alone.

Important: the YubiKey is not the documentation. It only enables technical access. The next steps are documented here.

## Where Is The Documentation?

The internal documentation is available at:

```text
https://docs.home
```

This address only works from the home network or through VPN.

Useful starting points:

- [Backups](./backup.md)
- [Post-Migration Ops](./post-migration-ops.md)
- [Network Isolation](./network-isolation.md)
- [Storage Array ZFS](./storage-array-zfs.md)

For non-technical orientation, use the onboarding presentation:

- [Homelab Onboarding](./presentations/homelab-onboarding.md)

## Passwords In An Emergency

Passwords are managed in Bitwarden. Emergency access should be handled through Bitwarden Emergency Access.

That means:

- the trusted person signs in with their own Bitwarden account
- they request emergency access
- access is released after the configured waiting period
- after release, the shared passwords can be viewed or taken over

The waiting period is intentional. It protects against accidental or unauthorized immediate access.

## How To Request Bitwarden Emergency Access

From the trusted person's perspective:

1. Open Bitwarden.
2. Sign in with your own Bitwarden account.
3. Open **Settings**.
4. Open **Emergency Access**.
5. Request access.
6. Wait until Bitwarden releases access after the configured waiting period.
7. Search for the relevant credentials after access is granted.

If technical help is needed, involve Michael or Fabian after the required credentials are available.

## What To Do First

In an emergency:

1. Stay calm and do not delete anything on the server.
2. Request Bitwarden Emergency Access if passwords are needed.
3. Contact Michael or Fabian if technical help is needed.
4. Open this documentation and follow the existing runbooks.
5. Before making larger changes, check whether a current backup exists.

## What Not To Do

Do not:

- delete containers, data directories, or backups
- blindly change passwords
- rebuild services before existing data has been checked
- clean up old server files before checking the backup state
- share secret values in GitHub, chats, or screenshots

## Important Locations

```text
Production path:
/home/github/homelab

Local configuration on the server:
/home/github/homelab/.env

Secrets on the server:
/home/github/homelab/secrets/

Persistent service data:
/home/github/homelab/data/

Backups:
/home/github/homelab/backups/
```

The `.env`, `secrets/`, `data/`, and `backups/` paths are not meant for GitHub.

## Short Version

For family members:

1. Open Bitwarden.
2. Request Emergency Access.
3. Involve Michael or Fabian.
4. Do not delete data.

For Michael or Fabian:

1. Access the server with the YubiKey.
2. Read the documentation at `docs.home`.
3. Check the current state.
4. Check the backup state.
5. Make changes only after that.
