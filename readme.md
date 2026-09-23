# Virtual Dungeon Master

VDM is being rebuilt as a multiplayer storytelling and tabletop platform. The `dev` branch is an orphan branch for the new implementation. The legacy code remains on `main` and in local ignored `backend/` and `frontend_old/` directories during the migration.

## Current build

The development build has a FastAPI service, four isolated SQLite databases, registration and revocable browser sessions, room creation and joining, role-gated live messages, a React story interface, and GM-requested AI narration. D&D 3.5e rooms have an initial JSON-backed character sheet editor and server-resolved ability and skill checks. Freeform storytelling rooms do not require sheets. Turn arbitration, voice, and the remaining ruleset mechanics are still under development. See [roadmap.md](roadmap.md) for the next milestones.

## Run locally

Install [uv](https://docs.astral.sh/uv/), then run:

```powershell
uv sync --group dev --python 3.12
cd frontend
npm ci
npm run build
cd ..
uv run uvicorn vdm.main:app --host 127.0.0.1 --port 8000 --reload
```

Open <http://127.0.0.1:8000/>. The health endpoint is <http://127.0.0.1:8000/api/health>.

For frontend hot reload, run `npm run dev` from `frontend/` while the backend runs on port 8000. Vite proxies `/api` HTTP and WebSocket traffic to the backend.

Copy `vdm.example.yaml` to `vdm.yaml` for local defaults, or `.env.example` to `.env`. Settings use the `VDM_` prefix and environment variables take precedence over YAML. Runtime data is stored under `data/` by default. Both local configuration and data are ignored by Git.

## Verify

```powershell
uv run pytest -q
uv run ruff check .
uv run mypy src
cd frontend && npm run build
```

On a restricted Windows shell, use `uv run pytest -q --basetemp .pytest-tmp` and set `UV_CACHE_DIR` to a writable workspace path.

## Deployment

See [docs/deployment.md](docs/deployment.md) for the intended `z1-hestia` process and validation checks. Preserve any existing server data until its layout has been inspected and backed up.
