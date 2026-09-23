"""3.5e sheet ownership, migration, and server-resolved checks."""

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from vdm.characters import Character, validate_sheet
from vdm.config import Settings
from vdm.dnd35e import ability_modifier, resolve_check
from vdm.main import create_app
from vdm.storage.sqlite import Domain, SqliteStorage


def _login(client: TestClient, name: str) -> str:
    credentials = {"username": name, "password": "correct horse battery staple"}
    assert client.post("/api/auth/register", json=credentials).status_code == 201
    assert client.post("/api/auth/login", json=credentials).status_code == 200
    return client.get("/api/auth/me").json()["id"]


def test_campaign_schema_upgrades_without_losing_characters(tmp_path: Path) -> None:
    """The existing version-1 character table gains version columns in place."""
    storage = SqliteStorage(tmp_path)
    storage.initialize()
    with storage.connect(Domain.CAMPAIGNS) as connection:
        connection.execute("PRAGMA user_version = 1")
        connection.execute("ALTER TABLE characters RENAME TO characters_old")
        connection.execute(
            "CREATE TABLE characters (id TEXT PRIMARY KEY, room_id TEXT, owner_id TEXT, "
            "name TEXT, sheet_json TEXT)"
        )
        connection.execute(
            "INSERT INTO characters VALUES ('c1', 'r1', 'u1', 'Old Hero', '{}')"
        )
        connection.execute("DROP TABLE characters_old")
    storage.initialize()
    with sqlite3.connect(storage.path_for(Domain.CAMPAIGNS)) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (2,)
        assert connection.execute(
            "SELECT name, version FROM characters WHERE id = 'c1'"
        ).fetchone() == ("Old Hero", 1)


def test_interrupted_campaign_migration_can_resume(tmp_path: Path) -> None:
    """A column added before an interrupted startup is not added twice."""
    storage = SqliteStorage(tmp_path)
    storage.initialize()
    with storage.connect(Domain.CAMPAIGNS) as connection:
        connection.execute("PRAGMA user_version = 1")
    storage.initialize()
    with storage.connect(Domain.CAMPAIGNS) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (2,)


def test_sheet_and_roll_permissions(tmp_path: Path) -> None:
    """Only 3.5e rooms have sheets; owners and GMs can save and roll."""
    app = create_app(Settings(data_dir=tmp_path, environment="development"))
    with TestClient(app) as host, TestClient(app) as player, TestClient(app) as other:
        _login(host, "HostUser")
        player_id = _login(player, "PlayerUser")
        _login(other, "OtherUser")
        freeform = host.post("/api/rooms", json={"name": "Story", "ruleset_id": "freeform"})
        freeform_id = freeform.json()["id"]
        assert host.get(f"/api/rooms/{freeform_id}/characters").status_code == 404
        assert host.post(
            f"/api/rooms/{freeform_id}/characters", json={"name": "No Sheet"}
        ).status_code == 422

        room = host.post("/api/rooms", json={"name": "3.5 Test", "ruleset_id": "dnd35e"})
        room_id = room.json()["id"]
        assert other.get(f"/api/rooms/{room_id}/characters").status_code == 404
        assert player.post(f"/api/rooms/{room_id}/join").status_code == 200
        sheet = {
            "abilities": {"STR": 9, "DEX": 16},
            "skills": {"Hide": {"ability": "DEX", "ranks": 2.5, "misc": 1}},
            "combat": {"hp_current": 8, "hp_max": 12},
            "equipment": [{"name": "Rope", "quantity": "1", "notes": "50 ft."}],
            "notes": "A quiet scout",
            "custom": {"portrait": "none"},
        }
        created = player.post(
            f"/api/rooms/{room_id}/characters", json={"name": "Scout", "sheet": sheet}
        )
        assert created.status_code == 201
        character = created.json()
        character_id = character["id"]
        assert character["owner_id"] == player_id
        assert character["sheet"]["abilities"]["WIS"] == 10
        assert character["sheet"]["level"] == 1
        assert character["sheet"]["class_name"] == ""
        assert character["sheet"]["custom"] == {"portrait": "none"}
        assert character["sheet"]["combat"]["hp_current"] == 8
        assert character["sheet"]["equipment"][0]["name"] == "Rope"
        assert len(host.get(f"/api/rooms/{room_id}/characters").json()) == 1

        assert host.post(
            f"/api/rooms/{room_id}/characters/{character_id}/checks",
            json={"kind": "skill", "target": "Hide", "dc": 12},
        ).status_code == 201
        event = host.get(f"/api/rooms/{room_id}/events").json()[0]
        assert event["kind"] == "roll"
        assert event["details"]["ability_modifier"] == 3
        assert event["details"]["ranks"] == 2.5
        assert event["details"]["misc"] == 1
        assert event["details"]["total"] == event["details"]["die"] + 6.5
        assert event["details"]["success"] == (event["details"]["total"] >= 12)

        assert player.post(
            f"/api/rooms/{room_id}/characters/{character_id}/checks",
            json={"kind": "skill", "target": "Missing"},
        ).status_code == 422
        assert player.post(
            f"/api/rooms/{room_id}/characters/{character_id}/checks",
            json={"kind": "ability", "target": "STR", "dc": 10},
        ).status_code == 403
        assert other.post(
            f"/api/rooms/{room_id}/characters/{character_id}/checks",
            json={"kind": "ability", "target": "STR"},
        ).status_code == 404
        assert other.post(f"/api/rooms/{room_id}/join").status_code == 200
        assert other.put(
            f"/api/rooms/{room_id}/characters/{character_id}",
            json={"name": "Stolen", "sheet": sheet, "version": 1},
        ).status_code == 403
        assert other.post(
            f"/api/rooms/{room_id}/characters/{character_id}/checks",
            json={"kind": "ability", "target": "STR"},
        ).status_code == 403

        updated = player.put(
            f"/api/rooms/{room_id}/characters/{character_id}",
            json={"name": "Scout II", "sheet": sheet, "version": 1},
        )
        assert updated.status_code == 200
        assert updated.json()["version"] == 2
        assert player.put(
            f"/api/rooms/{room_id}/characters/{character_id}",
            json={"name": "Overwritten", "sheet": sheet, "version": 1},
        ).status_code == 409


def test_sheet_validation_and_check_edge_cases() -> None:
    """Odd low scores round down; natural 1/20 do not override DCs."""
    assert ability_modifier(9) == -1
    assert ability_modifier(16) == 3
    sheet = validate_sheet({"abilities": {"STR": 9}})
    character = Character("c1", "r1", "u1", "Scout", sheet, 1, "now")
    low = resolve_check(character, "ability", "STR", 20, lambda: 20)
    assert low.total == 19
    assert low.success is False
    high = resolve_check(character, "ability", "STR", 0, lambda: 1)
    assert high.total == 0
    assert high.success is True


def test_expanded_sheet_defaults_and_entries_survive_validation() -> None:
    """Older sheets load and the new combat and inventory fields persist."""
    old = validate_sheet({"race": "Elf", "skills": {}})
    assert old["combat"]["speed"] == 30
    assert old["combat"]["saves"]["fortitude"] == {"base": 0, "misc": 0}
    assert old["attacks"] == old["equipment"] == old["spells"] == old["feats"] == []

    expanded = validate_sheet({
        "alignment": "Neutral Good", "experience": 1200,
        "combat": {"hp_current": 8, "hp_max": 12, "armor": 4,
                   "saves": {"reflex": {"base": 3, "misc": 1}}},
        "attacks": [{"name": "Longsword", "bonus": "+4", "damage": "1d8+2"}],
        "equipment": [{"name": "Rope", "quantity": "1", "notes": "50 ft."}],
        "feats": ["Weapon Focus"],
        "spells": [{"name": "Light", "level": "0", "notes": "At will"}],
    })
    assert expanded["combat"]["hp_current"] == 8
    assert expanded["combat"]["saves"]["reflex"]["base"] == 3
    assert expanded["attacks"][0]["damage"] == "1d8+2"
    assert expanded["spells"][0]["name"] == "Light"
