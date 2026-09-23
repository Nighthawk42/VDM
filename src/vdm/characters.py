"""Room-scoped, JSON-backed character sheets with optimistic updates."""

import json
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any

from vdm.auth import User
from vdm.rooms import NARRATORS, Room
from vdm.storage.sqlite import Domain, SqliteStorage

ABILITIES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
MAX_SHEET_BYTES = 32_768


class CharacterConflict(Exception):
    """A stale sheet version was submitted."""


@dataclass(frozen=True)
class Character:
    """A character owned by a room member."""

    id: str
    room_id: str
    owner_id: str
    name: str
    sheet: dict[str, Any]
    version: int
    updated_at: str


def validate_sheet(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate core 3.5e fields while preserving additional JSON fields."""
    sheet = dict(raw)
    for key in ("race", "class_name"):
        value = sheet.get(key, "")
        if not isinstance(value, str) or len(value) > 80:
            raise ValueError(f"{key} must be text of at most 80 characters")
        sheet[key] = value
    level = sheet.get("level", 1)
    if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= 99:
        raise ValueError("Level must be a whole number from 1 to 99")
    sheet["level"] = level
    abilities = sheet.get("abilities", {})
    if not isinstance(abilities, dict) or any(key not in ABILITIES for key in abilities):
        raise ValueError("Abilities must use STR, DEX, CON, INT, WIS, and CHA")
    for ability in ABILITIES:
        score = abilities.get(ability, 10)
        if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 99:
            raise ValueError(f"{ability} must be a whole number from 1 to 99")
    sheet["abilities"] = {ability: abilities.get(ability, 10) for ability in ABILITIES}

    skills = sheet.get("skills", {})
    if not isinstance(skills, dict) or len(skills) > 100:
        raise ValueError("Skills must be an object with at most 100 entries")
    for name, entry in skills.items():
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60:
            raise ValueError("Skill names must be 1-60 characters")
        if not isinstance(entry, dict) or set(entry) != {"ability", "ranks", "misc"}:
            raise ValueError(f"{name}: provide ability, ranks, and misc")
        if entry["ability"] not in ABILITIES:
            raise ValueError(f"{name}: unknown ability")
        ranks = entry["ranks"]
        misc = entry["misc"]
        if (
            isinstance(ranks, bool)
            or not isinstance(ranks, (int, float))
            or not 0 <= ranks <= 100
            or ranks * 2 != int(ranks * 2)
        ):
            raise ValueError(f"{name}: ranks must use half-rank steps from 0 to 100")
        if isinstance(misc, bool) or not isinstance(misc, int) or not -100 <= misc <= 100:
            raise ValueError(f"{name}: misc must be a whole number from -100 to 100")
    sheet["skills"] = skills
    notes = sheet.get("notes", "")
    if not isinstance(notes, str) or len(notes) > 4000:
        raise ValueError("Notes must be text of at most 4000 characters")
    sheet["notes"] = notes
    try:
        encoded = json.dumps(sheet, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("Sheet must contain valid JSON values") from exc
    if len(encoded.encode("utf-8")) > MAX_SHEET_BYTES:
        raise ValueError("Sheet exceeds 32 KB")
    return sheet


class CharacterService:
    """Persist characters in the campaign database only."""

    def __init__(self, storage: SqliteStorage) -> None:
        self.storage = storage

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Character:
        return Character(
            row["id"], row["room_id"], row["owner_id"], row["name"],
            validate_sheet(json.loads(row["sheet_json"])), row["version"], row["updated_at"],
        )

    def list_for(self, room: Room) -> list[Character]:
        """List shared player sheets in a joined room."""
        with self.storage.connect(Domain.CAMPAIGNS) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT * FROM characters WHERE room_id = ? ORDER BY name COLLATE NOCASE, id",
                (room.id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, room: Room, character_id: str) -> Character | None:
        """Find a character only within its room."""
        with self.storage.connect(Domain.CAMPAIGNS) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM characters WHERE room_id = ? AND id = ?",
                (room.id, character_id),
            ).fetchone()
        return self._from_row(row) if row else None

    def create(self, room: Room, user: User, name: str, sheet: dict[str, Any]) -> Character:
        """Create a member-owned character in a 3.5e room."""
        if room.ruleset_id != "dnd35e":
            raise ValueError("Character sheets are available for 3.5e rooms")
        if room.role.value == "spectator":
            raise PermissionError("Spectators cannot create characters")
        name = name.strip()
        if not 1 <= len(name) <= 80:
            raise ValueError("Character name must be 1-80 characters")
        checked = validate_sheet(sheet)
        character_id = uuid.uuid4().hex
        with self.storage.connect(Domain.CAMPAIGNS) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute(
                "INSERT INTO characters (id, room_id, owner_id, name, sheet_json, updated_at) "
                "VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (character_id, room.id, user.id, name, json.dumps(checked)),
            )
            row = connection.execute(
                "SELECT * FROM characters WHERE id = ?", (character_id,)
            ).fetchone()
        return self._from_row(row)

    def update(
        self, room: Room, user: User, character: Character,
        name: str, sheet: dict[str, Any], version: int,
    ) -> Character:
        """Update a sheet only when the owner or GM has its current version."""
        if room.role.value == "spectator":
            raise PermissionError("Spectators cannot edit characters")
        if user.id != character.owner_id and room.role not in NARRATORS:
            raise PermissionError("Only the owner or GM can edit this character")
        name = name.strip()
        if not 1 <= len(name) <= 80:
            raise ValueError("Character name must be 1-80 characters")
        checked = validate_sheet(sheet)
        with self.storage.connect(Domain.CAMPAIGNS) as connection:
            connection.row_factory = sqlite3.Row
            changed = connection.execute(
                "UPDATE characters SET name = ?, sheet_json = ?, version = version + 1, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ? AND room_id = ? AND version = ?",
                (name, json.dumps(checked), character.id, room.id, version),
            ).rowcount
            if not changed:
                raise CharacterConflict("Character changed elsewhere; reload before saving")
            row = connection.execute(
                "SELECT * FROM characters WHERE id = ?", (character.id,)
            ).fetchone()
        return self._from_row(row)
