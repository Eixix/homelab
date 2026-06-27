# Storage Array ZFS Review

This captures the current production state of `/storage_array` and the hardening items to decide before changing pool or dataset settings.

## Current State

Observed on production:

```text
pool: storage_array
state: ONLINE
layout: mirror-0 with sda and sdb
capacity: 24%
fragmentation: 1%
last scrub: 2026-06-14, repaired 0B, 0 errors
mountpoint: /storage_array
```

Dataset properties:

```text
compression=off
atime=on
relatime=off
recordsize=128K
xattr=on
acltype=off
exec=on
setuid=on
devices=on
snapdir=hidden
```

Snapshot/scrub scheduling:

- Monthly scrub is configured through `/etc/cron.d/zfsutils-linux` on the second Sunday of each month.
- Weekly snapshots are enabled through `/etc/cron.weekly/zfs-auto-snapshot` with `--keep=8`.
- Monthly snapshots are enabled through `/etc/cron.monthly/zfs-auto-snapshot` with `--keep=12`.
- Frequent and daily snapshots are effectively disabled.
- Old daily snapshots from 2023 are still present and should be reviewed before deletion.
- ZED is enabled and configured to notify `root`; confirm root mail is actually delivered to a monitored mailbox or replace it with the existing n8n notification path.

Rechecked on 2026-06-27:

- Pool remains `ONLINE`; last scrub still reports `0` errors.
- `compression=off` and `atime=on` are still inherited from defaults.
- A bounded scan found no setuid files or device nodes in the sample, but many media/document files have executable bits set. Treat `exec=off` as desirable for future media/document datasets, but do not flip it on the root dataset without a service-aware maintenance window.
- ZED still only targets `root` mail through `ZED_EMAIL_ADDR="root"`.

## Recommended Changes

First low-risk pass:

```bash
sudo zfs set compression=lz4 storage_array
sudo zfs set atime=off storage_array
```

Those changes affect new writes and metadata behavior without moving data or changing service-visible paths. They are the safest immediate hardening/performance win for the current single-dataset layout.

Consider dataset separation instead of keeping everything on the root dataset:

```bash
sudo zfs create storage_array/photos
sudo zfs create storage_array/books
sudo zfs create storage_array/documents
```

Only do that with a migration plan, because paths such as `/storage_array/Photos`, `/storage_array/books`, and `/storage_array/documents` are already used by services and backups.

Security properties need service-by-service review before changing:

```bash
sudo zfs set devices=off storage_array
sudo zfs set setuid=off storage_array
sudo zfs set exec=off storage_array
```

Those settings are good defaults for pure media/document datasets, but they can break workloads if anything on `/storage_array` needs executable files, device nodes, or setuid behavior.

Recommended sequence:

1. Apply `compression=lz4` and `atime=off` on `storage_array`.
2. Leave `exec`, `setuid`, and `devices` unchanged on the root dataset for now.
3. During dataset separation, set stricter properties on pure media/document datasets, for example `exec=off`, `setuid=off`, and `devices=off`.
4. Replace or test ZED root mail delivery with a monitored notification path.

## Verification Commands

```bash
zpool status storage_array
zpool list storage_array
zfs list -o name,mountpoint,used,avail,compression,compressratio,atime,recordsize,xattr,acltype storage_array
zfs list -t snapshot -o name,creation,used -s creation storage_array
systemctl status zfs-zed.service
systemctl list-timers --all | grep -Ei 'zfs|scrub|snapshot|sanoid|syncoid'
```
