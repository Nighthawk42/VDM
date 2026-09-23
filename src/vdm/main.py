"""ASGI application and startup lifecycle."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

import httpx
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
from vdm.characters import Character, CharacterConflict, CharacterService
from vdm.config import Settings, load_settings
from vdm.dnd35e import resolve_check
from vdm.openrouter import NarrationError, narrate
from vdm.rooms import NARRATORS, RULESETS, Event, Room, RoomService
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


class CharacterCreate(BaseModel):
    """A simple editor's character name and flexible sheet document."""

    name: str = Field(min_length=1, max_length=80)
    sheet: dict[str, Any] = Field(default_factory=dict)


class CharacterUpdate(CharacterCreate):
    """Require a version to prevent overwriting another editor's changes."""

    version: int = Field(ge=1)


class CheckCreate(BaseModel):
    """A requested 3.5e ability or skill check."""

    kind: Literal["ability", "skill"]
    target: str = Field(min_length=1, max_length=60)
    dc: int | None = Field(default=None, ge=0, le=100)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an app with independently injectable runtime settings."""
    config = settings or load_settings()
    storage = SqliteStorage(config.data_dir)
    auth = AuthService(storage)
    rooms = RoomService(storage)
    characters = CharacterService(storage)
    connections: dict[str, set[WebSocket]] = {}
    narration_locks: dict[str, asyncio.Lock] = {}

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

    @app.get("/api/audio/health")
    async def audio_health(_user: User = Depends(current_user)) -> dict[str, str]:
        """Check the configured local audio.cpp service without exposing its address."""
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response = await client.get(f"{config.audio_cpp_url.rstrip('/')}/health")
                response.raise_for_status()
                payload = response.json()
            if payload.get("status") != "ok":
                raise ValueError("Audio service is not ready")
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise HTTPException(status_code=503, detail="Audio service is unavailable") from exc
        return {"status": "ok", "backend": str(payload.get("backend", "unknown"))}

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

    @app.get("/api/rooms/{room_id}/characters")
    def list_characters(room_id: str, user: User = Depends(current_user)) -> list[Character]:
        """List shared character sheets in a 3.5e room."""
        room = member_room(room_id, user)
        if room.ruleset_id != "dnd35e":
            raise HTTPException(status_code=404, detail="Character sheets are not used here")
        return characters.list_for(room)

    @app.post("/api/rooms/{room_id}/characters", status_code=201)
    def create_character(
        room_id: str, body: CharacterCreate, user: User = Depends(current_user)
    ) -> Character:
        """Create a character owned by the signed-in room member."""
        room = member_room(room_id, user)
        try:
            return characters.create(room, user, body.name, body.sheet)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.put("/api/rooms/{room_id}/characters/{character_id}")
    def update_character(
        room_id: str, character_id: str, body: CharacterUpdate,
        user: User = Depends(current_user),
    ) -> Character:
        """Save a sheet if its version is current and the caller may edit it."""
        room = member_room(room_id, user)
        character = characters.get(room, character_id)
        if character is None:
            raise HTTPException(status_code=404, detail="Character not found")
        try:
            return characters.update(room, user, character, body.name, body.sheet, body.version)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except CharacterConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/rooms/{room_id}/characters/{character_id}/checks", status_code=201)
    async def roll_check(
        room_id: str, character_id: str, body: CheckCreate,
        user: User = Depends(current_user),
    ) -> Event:
        """Roll on the server and publish an auditable result to the chronicle."""
        room = member_room(room_id, user)
        if room.ruleset_id != "dnd35e":
            raise HTTPException(status_code=404, detail="Checks are not used here")
        character = characters.get(room, character_id)
        if character is None:
            raise HTTPException(status_code=404, detail="Character not found")
        if user.id != character.owner_id and room.role not in NARRATORS:
            raise HTTPException(
                status_code=403, detail="Only the owner or GM can roll for this character"
            )
        if body.dc is not None and room.role not in NARRATORS:
            raise HTTPException(status_code=403, detail="Only a GM can set a check DC")
        try:
            result = resolve_check(character, body.kind, body.target, body.dc)
            bonus = result.ability_modifier + result.ranks + result.misc
            content = (
                f"{character.name} · {body.target} check: d20 {result.die} "
                f"{bonus:+g} = {result.total:g}"
            )
            if body.dc is not None:
                content += f" vs DC {body.dc} — {'success' if result.success else 'failure'}"
            event = rooms.record_check(room, user, content, result.details())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        await broadcast(room_id, event)
        return event

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

    @app.post("/api/rooms/{room_id}/narrate", status_code=201)
    async def narrate_room(room_id: str, user: User = Depends(current_user)) -> Event:
        """Let a room GM request one AI continuation, then publish it to the chronicle."""
        room = member_room(room_id, user)
        if room.role not in NARRATORS:
            raise HTTPException(status_code=403, detail="Only a GM can request narration")
        lock = narration_locks.setdefault(room_id, asyncio.Lock())
        if lock.locked():
            raise HTTPException(status_code=409, detail="Narration already in progress")
        async with lock:
            try:
                prose = await narrate(config, room, rooms.history(user, room_id))
            except NarrationError as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            try:
                event = rooms.post(room, user, "narration", prose)
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
