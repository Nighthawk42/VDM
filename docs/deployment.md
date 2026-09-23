# Testing deployment on z1-hestia

The hostname or SSH alias must be reachable before any server changes. On the host, first identify the existing VDM service, reverse proxy, working directory, and data volumes. Record their paths and make a backup of any persistent database and user assets. Do not reuse the old database files with the new four-domain schema.

The new application is an ASGI service. From a checkout of `dev`, install the pinned environment with `uv sync --locked --no-dev --python 3.12`. Configure `VDM_ENVIRONMENT=testing` and an absolute `VDM_DATA_DIR` in a private environment file. Run `uv run --no-dev uvicorn vdm.main:app --host 127.0.0.1 --port <private-port>` under the host's service manager. The reverse proxy for `vdm.nighthawk.moe` should target that private port.

Before switching the public route, verify `GET /api/health` returns HTTP 200 locally and that the root page loads. After switching, verify HTTPS, the same endpoints through the public hostname, and the service logs. Keep the old deployment and data available for rollback until the new build is confirmed.
