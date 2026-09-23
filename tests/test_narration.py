"""GM narration permissions and provider failure behavior."""

from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from vdm.config import Settings
from vdm.main import create_app
from vdm.rooms import Event, Room


def _login(client: TestClient, username: str) -> None:
    credentials = {"username": username, "password": "correct horse battery staple"}
    assert client.post("/api/auth/register", json=credentials).status_code == 201
    assert client.post("/api/auth/login", json=credentials).status_code == 200


def test_only_gm_can_request_narration(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """A GM request is stored once, while player requests never call the provider."""
    calls: list[str] = []

    async def fake_narrate(settings: Settings, room: Room, events: list[Event]) -> str:
        calls.append(room.id)
        assert settings.openrouter_model == "openai/gpt-6-luna"
        assert events[-1].content == "I open the door."
        return "A bell rings beyond the door."

    monkeypatch.setattr("vdm.main.narrate", fake_narrate)
    app = create_app(Settings(data_dir=tmp_path, openrouter_api_key="test-only"))
    with TestClient(app) as host, TestClient(app) as player:
        _login(host, "HostUser")
        _login(player, "PlayerUser")
        room_id = host.post("/api/rooms", json={"name": "The Lantern"}).json()["id"]
        player.post(f"/api/rooms/{room_id}/join")
        host.post(
            f"/api/rooms/{room_id}/events",
            json={"kind": "action", "content": "I open the door."},
        )
        assert player.post(f"/api/rooms/{room_id}/narrate").status_code == 403
        result = host.post(f"/api/rooms/{room_id}/narrate")
        assert result.status_code == 201
        assert result.json()["content"] == "A bell rings beyond the door."
        assert calls == [room_id]
        assert [event["kind"] for event in host.get(f"/api/rooms/{room_id}/events").json()] == [
            "action",
            "narration",
        ]


def test_narration_requires_configuration(tmp_path: Path) -> None:
    """A missing provider key fails clearly without storing a placeholder event."""
    app = create_app(Settings(data_dir=tmp_path, openrouter_api_key=None))
    with TestClient(app) as host:
        _login(host, "HostUser")
        room_id = host.post("/api/rooms", json={"name": "The Lantern"}).json()["id"]
        host.post(
            f"/api/rooms/{room_id}/events",
            json={"kind": "action", "content": "I open the door."},
        )
        result = host.post(f"/api/rooms/{room_id}/narrate")
        assert result.status_code == 503
        assert result.json()["detail"] == "AI narration is not configured"
        assert len(host.get(f"/api/rooms/{room_id}/events").json()) == 1
