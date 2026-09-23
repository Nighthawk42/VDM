"""ASGI application and startup lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from vdm.auth import SESSION_DAYS, AuthService, User
from vdm.config import Settings, load_settings
from vdm.rooms import RULESETS, Event, Room, RoomService
from vdm.storage.sqlite import SqliteStorage

INDEX_PATH = Path(__file__).with_name("static") / "index.html"
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
COOKIE_NAME = "vdm_session"


class Credentials(BaseModel):
    """Shared username/password validation for registration and login."""

    username: str = Field(min_length=3, max_length=20, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    password: str = Field(min_length=12, max_length=256)


class RoomCreate(BaseModel):
    """A new room's editable properties."""

    name: str = Field(min_length=1, max_length=80)
    ruleset_id: str = "freeform"


class MessageCreate(BaseModel):
    """A participant's new message."""

    kind: Literal["action", "ooc", "narration"]
    content: str = Field(min_length=1, max_length=4000)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an app with independently injectable runtime settings."""
    config = settings or load_settings()
    storage = SqliteStorage(config.data_dir)
    auth = AuthService(storage)
    rooms = RoomService(storage)
    connections: dict[str, set[WebSocket]] = {}

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        storage.initialize()
        yield

    app = FastAPI(title=config.app_name, lifespan=lifespan)
    app.state.settings = config
    app.state.storage = storage
    if (FRONTEND_DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    def current_user(request: Request) -> User:
        user = auth.authenticate(request.cookies.get(COOKIE_NAME))
        if user is None:
            raise HTTPException(status_code=401, detail="Sign in required")
        return user

    def member_room(room_id: str, user: User) -> Room:
        room = rooms.get(user, room_id)
        if room is None:
            raise HTTPException(status_code=404, detail="Room not found")
        return room

    async def broadcast(room_id: str, event: Event) -> None:
        frame = {"type": "event", "event": event.__dict__}
        for peer in tuple(connections.get(room_id, ())):
            try:
                await peer.send_json(frame)
            except (RuntimeError, OSError):
                connections[room_id].discard(peer)

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        """Show the development landing page."""
        built_index = FRONTEND_DIST / "index.html"
        return FileResponse(built_index if built_index.is_file() else INDEX_PATH)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        """Expose readiness for local checks and deployment monitoring."""
        if not storage.is_ready():
            raise HTTPException(status_code=503, detail="Storage is not ready")
        return {"status": "ok", "environment": config.environment}

    @app.post("/api/auth/register", status_code=201)
    def register(credentials: Credentials) -> User:
        """Create a player account; registration does not grant platform admin."""
        try:
            return auth.register(credentials.username, credentials.password)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/auth/login")
    def login(credentials: Credentials, response: Response) -> User:
        """Issue a revocable, HttpOnly session cookie."""
        result = auth.login(credentials.username, credentials.password)
        if result is None:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        user, token = result
        response.set_cookie(
            COOKIE_NAME,
            token,
            max_age=SESSION_DAYS * 24 * 60 * 60,
            httponly=True,
            secure=config.environment != "development",
            samesite="strict",
            path="/",
        )
        return user

    @app.post("/api/auth/logout", status_code=204)
    def logout(request: Request, response: Response) -> None:
        """Revoke the current browser session."""
        auth.logout(request.cookies.get(COOKIE_NAME))
        response.delete_cookie(COOKIE_NAME, path="/", samesite="strict")

    @app.get("/api/auth/me")
    def me(user: User = Depends(current_user)) -> User:
        """Return the signed-in account."""
        return user

    @app.post("/api/rooms", status_code=201)
    def create_room(body: RoomCreate, user: User = Depends(current_user)) -> Room:
        """Create a room with the caller as host."""
        if body.ruleset_id not in RULESETS:
            raise HTTPException(status_code=422, detail="Unsupported ruleset")
        if not body.name.strip():
            raise HTTPException(status_code=422, detail="Room name is required")
        return rooms.create(user, body.name, body.ruleset_id)

    @app.get("/api/rooms")
    def list_rooms(user: User = Depends(current_user)) -> list[Room]:
        """List rooms joined by the caller."""
        return rooms.list_for(user)

    @app.post("/api/rooms/{room_id}/join")
    def join_room(room_id: str, user: User = Depends(current_user)) -> Room:
        """Join a room using its link ID."""
        room = rooms.join(user, room_id)
        if room is None:
            raise HTTPException(status_code=404, detail="Room not found")
        return room

    @app.get("/api/rooms/{room_id}")
    def get_room(room_id: str, user: User = Depends(current_user)) -> Room:
        """Read one joined room."""
        return member_room(room_id, user)

    @app.get("/api/rooms/{room_id}/events")
    def room_events(room_id: str, user: User = Depends(current_user)) -> list[Event]:
        """Read recent messages from a joined room."""
        member_room(room_id, user)
        return rooms.history(user, room_id)

    @app.post("/api/rooms/{room_id}/events", status_code=201)
    async def post_event(
        room_id: str, body: MessageCreate, user: User = Depends(current_user)
    ) -> Event:
        """Post a message and fan it out to connected room members."""
        room = member_room(room_id, user)
        if not body.content.strip():
            raise HTTPException(status_code=422, detail="Message is empty")
        try:
            event = rooms.post(room, user, body.kind, body.content.strip())
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        await broadcast(room_id, event)
        return event

    @app.websocket("/api/rooms/{room_id}/ws")
    async def room_socket(websocket: WebSocket, room_id: str) -> None:
        """Stream room events with a membership check on every incoming frame."""
        await websocket.accept()
        user = auth.authenticate(websocket.cookies.get(COOKIE_NAME))
        if user is None:
            await websocket.close(code=4401)
            return
        if rooms.get(user, room_id) is None:
            await websocket.close(code=4403)
            return
        connections.setdefault(room_id, set()).add(websocket)
        await websocket.send_json({
            "type": "history",
            "events": [event.__dict__ for event in rooms.history(user, room_id)],
        })
        try:
            while True:
                try:
                    body = MessageCreate.model_validate(await websocket.receive_json())
                except (ValidationError, ValueError):
                    await websocket.send_json({"type": "error", "detail": "Invalid message"})
                    continue
                room = rooms.get(user, room_id)
                if room is None:
                    await websocket.close(code=4403)
                    break
                if not body.content.strip():
                    await websocket.send_json({"type": "error", "detail": "Message is empty"})
                    continue
                try:
                    event = rooms.post(room, user, body.kind, body.content.strip())
                except PermissionError as exc:
                    await websocket.send_json({"type": "error", "detail": str(exc)})
                    continue
                await broadcast(room_id, event)
        except WebSocketDisconnect:
            pass
        finally:
            connections[room_id].discard(websocket)

    return app


app = create_app()
