"""Exercise account, room, permission, and live message behavior."""

from pathlib import Path

from fastapi.testclient import TestClient

from vdm.config import Settings
from vdm.main import create_app
from vdm.storage.sqlite import Domain, SqliteStorage


def _create_user(client: TestClient, name: str) -> None:
    credentials = {"username": name, "password": "correct horse battery staple"}
    assert client.post("/api/auth/register", json=credentials).status_code == 201
    assert client.post("/api/auth/login", json=credentials).status_code == 200


def test_accounts_and_revocable_sessions(tmp_path: Path) -> None:
    """A cookie authenticates a user, then logout revokes it."""
    app = create_app(Settings(data_dir=tmp_path, environment="development"))
    with TestClient(app) as client:
        assert client.get("/api/auth/me").status_code == 401
        _create_user(client, "Adventurer")
        assert client.get("/api/auth/me").json()["username"] == "Adventurer"
        assert client.post(
            "/api/auth/register",
            json={"username": "adventurer", "password": "another long password"},
        ).status_code == 409
        assert client.post(
            "/api/auth/login",
            json={"username": "Adventurer", "password": "incorrect password"},
        ).status_code == 401
        assert client.post("/api/auth/logout").status_code == 204
        assert client.get("/api/auth/me").status_code == 401


def test_room_access_and_live_messages(tmp_path: Path) -> None:
    """Members can exchange messages; spectators cannot write or narrate."""
    app = create_app(Settings(data_dir=tmp_path, environment="development"))
    with TestClient(app) as host, TestClient(app) as player:
        _create_user(host, "HostUser")
        _create_user(player, "PlayerUser")
        response = host.post("/api/rooms", json={"name": "The Lantern", "ruleset_id": "freeform"})
        assert response.status_code == 201
        room_id = response.json()["id"]
        assert response.json()["role"] == "host"
        assert player.get(f"/api/rooms/{room_id}").status_code == 404
        assert player.post(f"/api/rooms/{room_id}/join").json()["role"] == "player"
        assert player.get("/api/rooms").json()[0]["id"] == room_id

        with (
            host.websocket_connect(f"/api/rooms/{room_id}/ws") as host_socket,
            player.websocket_connect(f"/api/rooms/{room_id}/ws") as player_socket,
        ):
            assert host_socket.receive_json()["type"] == "history"
            assert player_socket.receive_json()["type"] == "history"
            posted = player.post(
                f"/api/rooms/{room_id}/events",
                json={"kind": "action", "content": "I open the door."},
            )
            assert posted.status_code == 201
            assert host_socket.receive_json()["event"]["content"] == "I open the door."
            assert player_socket.receive_json()["event"]["content"] == "I open the door."

        assert player.post(
            f"/api/rooms/{room_id}/events",
            json={"kind": "narration", "content": "The door opens."},
        ).status_code == 403
        assert host.post(
            f"/api/rooms/{room_id}/events",
            json={"kind": "narration", "content": "The door opens."},
        ).status_code == 201
        history = player.get(f"/api/rooms/{room_id}/events").json()
        assert [item["kind"] for item in history] == ["action", "narration"]

        storage = SqliteStorage(tmp_path)
        with storage.connect(Domain.CAMPAIGNS) as connection:
            connection.execute(
                "UPDATE memberships SET role = 'spectator' WHERE room_id = ? AND role = 'player'",
                (room_id,),
            )
        assert player.post(
            f"/api/rooms/{room_id}/events",
            json={"kind": "action", "content": "I open another door."},
        ).status_code == 403
