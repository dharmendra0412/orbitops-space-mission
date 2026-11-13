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


## Deploy the website on Vercel

The repository is configured as a single Vercel FastAPI project. The Python app serves the read-only API and mounts the built Vite website at the root path, so the browser uses same-origin `/api/*` requests.

1. Push the feature branch to GitHub and open [Vercel New Project](https://vercel.com/new).
2. Import `dharmendra0412/orbitops-space-mission`.
3. Keep the project root directory set to the repository root (not `backend/`).
4. Vercel should detect the FastAPI project from `pyproject.toml`. The configured build script runs `npm install && npm run build` before deploying the Python app.
5. Deploy a Preview first. Verify the homepage, `/health`, `/docs`, and one live PDS request such as `/api/v1/pds/search?keywords=LOLA`.
6. Only after Preview checks pass, connect the production domain and promote/deploy to Production from Vercel.

No `VITE_API_BASE_URL` or CORS environment variable is required for the single-origin deployment. Leave `VITE_API_BASE_URL` empty so the frontend calls the same-origin API. Do not configure fake NASA data or sample fallback responses.

The FastAPI application is deployed as a Vercel Function; the Vite output is mounted as static frontend content. Vercel's Python runtime currently supports FastAPI and reads its entrypoint/dependencies from `pyproject.toml`. Check the current Vercel plan's function duration and resource limits against live archive requests before production use. The self-hosted Docker Compose instructions above remain an optional alternative, not the primary deployment path.
