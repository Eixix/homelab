# Traefik access logs

Traefik access events are written as JSON, collected by Grafana Alloy, stored in
Loki for 30 days, and explored through the internal Grafana instance.

## Before deployment

Set strong local values in the production `.env`:

```dotenv
GRAFANA_HOST=logs.home
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=replace-with-a-long-random-password
```

For every Cloudflare-proxied public zone, enable **Network > IP Geolocation**.
It is available on Cloudflare's free plan. Traefik records `CF-IPCountry` and
`CF-Ray`; it accepts forwarded client addresses only from Cloudflare's published
proxy ranges. Requests that do not pass through Cloudflare have no country label.

The country header itself is only trustworthy when the origin firewall rejects
direct public traffic to ports 80/443. Until that separate firewall control is
in place, treat country as an investigative hint because a direct client can
send a forged `CF-IPCountry` header. Do not automate blocking from this label.

The Cloudflare ranges are static Traefik configuration. Compare them periodically
with `https://www.cloudflare.com/ips/`, especially after a Cloudflare range-change
announcement.

## Deployment

Production remains manual-only. After the normal repository deployment, create
the runtime directories and start or recreate the affected services:

```sh
install -d -m 0750 data/traefik/logs data/monitoring/alloy
install -d -m 0750 -o 10001 -g 10001 data/monitoring/loki
install -d -m 0750 -o 472 -g 0 data/monitoring/grafana
docker compose --env-file .env --profile external config --quiet
docker compose --env-file .env up -d loki alloy grafana reverse-proxy
```

Install the repository-managed rotation policy once on the production host:

```sh
sudo ln -sfn /home/github/homelab/config/logrotate/traefik-access \
  /etc/logrotate.d/homelab-traefik-access
sudo logrotate --debug /etc/logrotate.d/homelab-traefik-access
```

The policy rotates daily or at 50 MiB, retains seven rotations, and signals
Traefik with `USR1` so it safely reopens the file. Loki retention is independent
and keeps ingested events for 30 days.

Open `https://${GRAFANA_HOST}`, then use the provisioned **Security / Traefik
access security** dashboard or Grafana Explore with the Loki data source.

Useful LogQL investigations:

```logql
{job="traefik-access", country_code="DE"} | json
```

```logql
{job="traefik-access"} | json | ClientHost="203.0.113.10"
```

```logql
{job="traefik-access"} | json | RequestHost="example.net" | DownstreamStatus >= 400
```

```logql
{job="traefik-access"} | json | request_CF_Ray="cloudflare-ray-id"
```

Exact parsed header names can differ in capitalization across Traefik releases;
open one event in Explore to confirm the JSON field shown by the deployed image.

## Data handling

Query parameters and all headers are dropped by default. Only User-Agent,
Referer, X-Request-ID, CF-IPCountry, and CF-Ray are retained. Never add cookies,
Authorization, or application tokens to access-log fields.

Country, host, and router are indexed as bounded Loki labels. Client IP, path,
User-Agent, request ID, and CF-Ray stay in the JSON event to avoid high-cardinality
indexes. Local Loki data is useful operational evidence but is not tamper-proof
against an attacker with host access.

## Later: individual container logs

Alloy is deliberately prepared as the common collector, but container-wide log
collection is not enabled yet. Add services individually after reviewing their
output for secrets and personal data. Prefer an allowlist of containers, parse
only useful low-cardinality labels, redact known sensitive fields in Alloy, and
use shorter retention for verbose application logs. Avoid granting Alloy access
to the Docker socket unless automatic discovery is worth that security exposure;
a Docker logging driver or explicit read-only log paths are safer alternatives.
