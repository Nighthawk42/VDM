"""Room membership, permissions, and chronicle persistence."""

import json
import secrets
import sqlite3
import uuid
from dataclasses import dataclass
from enum import StrEnum

from vdm.auth import User
from vdm.storage.sqlite import Domain, SqliteStorage


class Role(StrEnum):
    """Roles ordered by the room authority they carry."""

    HOST = "host"
    LEAD_GM = "lead_gm"
    CO_GM = "co_gm"
    PLAYER = "player"
    SPECTATOR = "spectator"


RULESETS = frozenset({"freeform", "dnd5e", "dnd35e", "starwars_rev"})
WRITERS = frozenset({Role.HOST, Role.LEAD_GM, Role.CO_GM, Role.PLAYER})
NARRATORS = frozenset({Role.HOST, Role.LEAD_GM, Role.CO_GM})


@dataclass(frozen=True)
class Room:
    """A room with the current user's membership role."""

    id: str
    name: str
    ruleset_id: str
    role: Role


@dataclass(frozen=True)
class Event:
    """A durable room message."""

    id: str
    room_id: str
    actor_id: str
    actor_name: str
    kind: str
    content: str
    created_at: str


class RoomService:
    """Keep access rules in one place for HTTP and WebSocket callers."""

    def __init__(self, storage: SqliteStorage) -> None:
        self.storage = storage

    def create(self, user: User, name: str, ruleset_id: str) -> Room:
        """Create a room and make its creator the host."""
        if ruleset_id not in RULESETS:
            raise ValueError("Unsupported ruleset")
        room = Room(secrets.token_urlsafe(9), name.strip(), ruleset_id, Role.HOST)
        with self.storage.connect(Domain.CAMPAIGNS) as connection:
            connection.execute(
                "INSERT INTO rooms (id, name, ruleset_id, created_by) VALUES (?, ?, ?, ?)",
                (room.id, room.name, room.ruleset_id, user.id),
            )
            connection.execute(
                "INSERT INTO memberships (room_id, user_id, role) VALUES (?, ?, ?)",
                (room.id, user.id, Role.HOST.value),
            )
        return room

    def join(self, user: User, room_id: str) -> Room | None:
        """Join an existing room as a player, preserving an existing role."""
        with self.storage.connect(Domain.CAMPAIGNS) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT id, name, ruleset_id FROM rooms WHERE id = ?", (room_id,)
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "INSERT OR IGNORE INTO memberships (room_id, user_id, role) VALUES (?, ?, ?)",
                (room_id, user.id, Role.PLAYER.value),
            )
            role_row = connection.execute(
                "SELECT role FROM memberships WHERE room_id = ? AND user_id = ?",
                (room_id, user.id),
            ).fetchone()
        return Room(row["id"], row["name"], row["ruleset_id"], Role(role_row["role"]))

    def get(self, user: User, room_id: str) -> Room | None:
        """Return a room only when the user is a member."""
        with self.storage.connect(Domain.CAMPAIGNS) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """SELECT r.id, r.name, r.ruleset_id, m.role FROM rooms AS r
                   JOIN memberships AS m ON m.room_id = r.id
                   WHERE r.id = ? AND m.user_id = ?""",
                (room_id, user.id),
            ).fetchone()
        if row is None:
            return None
        return Room(row["id"], row["name"], row["ruleset_id"], Role(row["role"]))

    def list_for(self, user: User) -> list[Room]:
        """List rooms the user may enter."""
        with self.storage.connect(Domain.CAMPAIGNS) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """SELECT r.id, r.name, r.ruleset_id, m.role FROM rooms AS r
                   JOIN memberships AS m ON m.room_id = r.id
                   WHERE m.user_id = ? ORDER BY r.created_at DESC, r.id DESC""",
                (user.id,),
            ).fetchall()
        return [Room(row["id"], row["name"], row["ruleset_id"], Role(row["role"])) for row in rows]

    def post(self, room: Room, user: User, kind: str, content: str) -> Event:
        """Store a room event after rechecking the caller's permission."""
        current_room = self.get(user, room.id)
        if current_room is None:
            raise PermissionError("Room membership is required")
        if kind == "narration":
            allowed = current_room.role in NARRATORS
        else:
            allowed = current_room.role in WRITERS and kind in {"action", "ooc"}
        if not allowed:
            raise PermissionError("Role cannot post this message")
        event_id = uuid.uuid4().hex
        payload = json.dumps({"content": content, "actor_name": user.username})
        with self.storage.connect(Domain.CHRONICLES) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute(
                """INSERT INTO events (id, room_id, actor_id, kind, payload_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (event_id, room.id, user.id, kind, payload),
            )
            row = connection.execute(
                "SELECT created_at FROM events WHERE id = ?", (event_id,)
            ).fetchone()
        return Event(event_id, room.id, user.id, user.username, kind, content, row["created_at"])

    def history(self, user: User, room_id: str, limit: int = 100) -> list[Event]:
        """Return recent events only to a current room member."""
        if self.get(user, room_id) is None:
            raise PermissionError("Room membership is required")
        with self.storage.connect(Domain.CHRONICLES) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """SELECT id, room_id, actor_id, kind, payload_json, created_at
                   FROM events WHERE room_id = ? ORDER BY rowid DESC LIMIT ?""",
                (room_id, limit),
            ).fetchall()
        return [
            Event(
                row["id"],
                row["room_id"],
                row["actor_id"],
                json.loads(row["payload_json"])["actor_name"],
                row["kind"],
                json.loads(row["payload_json"])["content"],
                row["created_at"],
            )
            for row in reversed(rows)
        ]
