"""Check startup and isolation of the four storage domains."""

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from vdm.config import Settings
from vdm.main import create_app
from vdm.storage.sqlite import Domain, SqliteStorage


def test_app_starts_with_separate_databases(tmp_path: Path) -> None:
    """Startup creates all domain files and serves a ready response."""
    app = create_app(Settings(data_dir=tmp_path, environment="test"))
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "environment": "test"}
        assert client.get("/").status_code == 200

    storage = SqliteStorage(tmp_path)
    assert all(storage.path_for(domain).is_file() for domain in Domain)
    with sqlite3.connect(storage.path_for(Domain.AUTH)) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
        assert "users" in tables
        assert "rooms" not in tables
    with sqlite3.connect(storage.path_for(Domain.CAMPAIGNS)) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
        assert "rooms" in tables
        assert "users" not in tables


def test_startup_is_idempotent(tmp_path: Path) -> None:
    """A restart preserves existing rows."""
    storage = SqliteStorage(tmp_path)
    storage.initialize()
    with storage.connect(Domain.AUTH) as connection:
        connection.execute(
            "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
            ("u1", "Player", "hash"),
        )
    storage.initialize()
    with storage.connect(Domain.AUTH) as connection:
        saved = connection.execute("SELECT username FROM users WHERE id = ?", ("u1",)).fetchone()
        assert saved == ("Player",)
