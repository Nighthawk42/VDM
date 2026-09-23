"""ASGI application and startup lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from vdm.config import Settings, load_settings
from vdm.storage.sqlite import SqliteStorage

INDEX_PATH = Path(__file__).with_name("static") / "index.html"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an app with independently injectable runtime settings."""
    config = settings or load_settings()
    storage = SqliteStorage(config.data_dir)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        storage.initialize()
        yield

    app = FastAPI(title=config.app_name, lifespan=lifespan)
    app.state.settings = config
    app.state.storage = storage

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        """Show the development landing page."""
        return FileResponse(INDEX_PATH)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        """Expose readiness for local checks and deployment monitoring."""
        if not storage.is_ready():
            raise HTTPException(status_code=503, detail="Storage is not ready")
        return {"status": "ok", "environment": config.environment}

    return app


app = create_app()
