# ORBITOPS self-hosted website

This Compose deployment serves the React website and its FastAPI read-only data API on one origin. Nginx forwards only `/api/` requests to the private API service; the API port is not published to the host.

## Requirements

- Docker Engine with the Compose plugin
- A host with outbound HTTPS access to the NASA PDS and JAXA/DARTS source endpoints used by the API

## Start

From the repository root:

```bash
docker compose up --build -d
```

Open `http://localhost:8080`. To choose another host port, set `ORBITOPS_WEB_PORT` before starting Compose, for example:

```bash
ORBITOPS_WEB_PORT=8090 docker compose up --build -d
```

## Verify and operate

```bash
docker compose ps
docker compose logs --tail=100 api web
curl -fsS http://localhost:8080/
curl -fsS http://localhost:8080/api/v1/pds/search?keywords=LOLA
docker compose down
```

The search command makes a live request to NASA PDS; an upstream outage is reported as an error, not replaced with sample results. The browser's mission brief remains local to that browser and is not uploaded to the API.

## Production notes

- Put a TLS-terminating reverse proxy or managed HTTPS load balancer in front of port 8080. Do not expose the plain HTTP port directly to the public internet.
- Restrict inbound host access to the proxy and keep the API service private on the Compose network.
- Pin image tags or digests to an approved patch level and rebuild regularly for security updates.
- Backups are not applicable to the current API because it has no server-side user database or mission-brief persistence.
- This deployment does not add authentication, multi-user accounts, mission simulation, or additional scientific data sources.
