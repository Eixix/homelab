# Service-Template

Dieses Template ist der Standardpfad fuer neue Web-UIs hinter Traefik.

## `.env`

```env
SERVICE_HOST=service.${DOMAIN_INTERNAL}
SERVICE_EXTERNAL_HOST=service.${DOMAIN_EXTERNAL}
```

## `compose/apps/service.yaml`

```yaml
services:
  service:
    container_name: service
    image: vendor/service:latest
    restart: unless-stopped
    cap_drop: [all]
    security_opt:
      - no-new-privileges:true
    environment:
      TZ: ${TZ}
    volumes:
      - ../../data/service:/config
    networks:
      - internal_network
    labels:
      - traefik.enable=true
      - traefik.http.routers.service.rule=Host(`${SERVICE_HOST}`)
      - traefik.http.routers.service.entrypoints=websecure
      - traefik.http.routers.service.tls=true
      - traefik.http.routers.service.tls.certresolver=internalresolver
      - traefik.http.routers.service.middlewares=lan-only@file,security-headers@file
      - traefik.http.services.service.loadbalancer.server.port=8080
      - traefik.docker.network=internal_network
```

## Checkliste

- Keine Secrets in Compose-Labels oder `.env.example`.
- Keine Host-Ports, ausser der Dienst muss wirklich direkt am Host lauschen.
- Keine Docker-Socket-Mounts, ausser es gibt keine bessere Alternative.
- Daten unter `data/<service>` oder bewusst dokumentierten externen Pfad legen.
- Datenbanken nur intern vernetzen, nicht ueber Traefik veroeffentlichen.
- `docker compose config --quiet` muss sauber durchlaufen.
