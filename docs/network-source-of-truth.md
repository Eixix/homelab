# Network source of truth

NetBox is the structured source of truth for the homelab network. It is available internally at `https://netbox.home`.

Use NetBox for sites, devices, interfaces, physical uplinks, VLANs, prefixes, IP addresses, DHCP ranges, WLANs, active clients, and server container inventory. Keep operational procedures and architectural decisions in this Docusaurus documentation.

## Automated UniFi synchronization

`scripts/sync-unifi-netbox.py` reads the live UniFi web API and updates NetBox idempotently. Credentials are supplied only through environment variables and must never be committed.

Required variables:

```text
UNIFI_URL=https://10.0.0.1
UNIFI_USERNAME=...
UNIFI_PASSWORD=...
NETBOX_URL=https://netbox.home
NETBOX_API_TOKEN=...
NETBOX_API_KEY=...
```

Optional server metadata variables:

```text
HOMELAB_SERVER_NAME=sun
HOMELAB_SERVER_IP=10.0.0.2
HOMELAB_SERVER_MAC=...
HOMELAB_SERVER_MODEL=...
HOMELAB_SERVER_DESCRIPTION=...
HOMELAB_CONTAINERS_FILE=/tmp/homelab-containers.json
```

The API token and key come from the ignored production `.env`. `NETBOX_API_TOKEN_PEPPER` is server-side key material and is required by NetBox, but is not passed to the importer.

The synchronization records UniFi infrastructure and active clients. A client which is no longer online is intentionally not deleted automatically; review stale records in NetBox before removing them.

## Backup and recovery

The regular homelab backup includes NetBox media, reports, scripts, configuration, and a logical PostgreSQL dump. Live PostgreSQL and Redis storage directories are excluded from the archive because the logical database dump is the consistent restore source.
