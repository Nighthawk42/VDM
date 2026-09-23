# Testing deployment on z1-hestia

The existing `vdm.nighthawk.moe` site is a separate, more complete VDM build under `/home/nighthawk/apps/vdm`. The backend runs as `vdm-backend.service` on `127.0.0.1:18600`; Caddy serves the React build from `/srv/vdm` and forwards `/api/*`, `/healthz`, and `/ws/*`. Its `data/vdm_core.db` contains persistent application state. Before switching the route, confirm this new `dev` branch is intended to replace that build and preserve its files and data for rollback. Do not reuse its database with the new four-domain schema.

The new application is an ASGI service. From a checkout of `dev`, install the pinned environment with `uv sync --locked --no-dev --python 3.12`. Configure `VDM_ENVIRONMENT=testing` and an absolute `VDM_DATA_DIR` in a private environment file. Run `uv run --no-dev uvicorn vdm.main:app --host 127.0.0.1 --port <private-port>` under the host's service manager. The current Caddy route also serves files from `/srv/vdm`, so it must be changed to proxy the root page to the new app.

Before switching the public route, verify `GET /api/health` returns HTTP 200 locally and that the root page loads. After switching, verify HTTPS, the same endpoints through the public hostname, and the service logs. Keep the old deployment and data available for rollback until the new build is confirmed.
