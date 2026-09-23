# Virtual Dungeon Master

VDM is being rebuilt as a multiplayer storytelling and tabletop platform. The `dev` branch is an orphan branch for the new implementation. The legacy code remains on `main` and in local ignored `backend/` and `frontend_old/` directories during the migration.

## Current build

This first build is a deployable foundation: a FastAPI service, a readiness endpoint, validated YAML/environment configuration, and four isolated SQLite databases for authentication, campaigns, chronicles, and memory. Gameplay and accounts are still under development. See [roadmap.md](roadmap.md) for the next milestones.

## Run locally

Install [uv](https://docs.astral.sh/uv/), then run:

```powershell
uv sync --group dev --python 3.12
uv run uvicorn vdm.main:app --host 127.0.0.1 --port 8000 --reload
```

Open <http://127.0.0.1:8000/>. The health endpoint is <http://127.0.0.1:8000/api/health>.

Copy `vdm.example.yaml` to `vdm.yaml` for local defaults, or `.env.example` to `.env`. Settings use the `VDM_` prefix and environment variables take precedence over YAML. Runtime data is stored under `data/` by default. Both local configuration and data are ignored by Git.

## Verify

```powershell
uv run pytest -q
uv run ruff check .
uv run mypy src
```

On a restricted Windows shell, use `uv run pytest -q --basetemp .pytest-tmp` and set `UV_CACHE_DIR` to a writable workspace path.

## Deployment

See [docs/deployment.md](docs/deployment.md) for the intended `z1-hestia` process and validation checks. Preserve any existing server data until its layout has been inspected and backed up.
