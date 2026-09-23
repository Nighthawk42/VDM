"""Split SQLite stores with idempotent schema initialization."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path


class Domain(StrEnum):
    """Independent database domains."""

    AUTH = "auth"
    CAMPAIGNS = "campaigns"
    CHRONICLES = "chronicles"
    MEMORY = "memory"


SCHEMAS: dict[Domain, str] = {
    Domain.AUTH: """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0 CHECK (is_admin IN (0, 1)),
            totp_secret TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """,
    Domain.CAMPAIGNS: """
        CREATE TABLE IF NOT EXISTS rooms (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            ruleset_id TEXT NOT NULL DEFAULT 'freeform',
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS memberships (
            room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK (
                role IN ('host', 'lead_gm', 'co_gm', 'player', 'spectator')
            ),
            PRIMARY KEY (room_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS characters (
            id TEXT PRIMARY KEY,
            room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
            owner_id TEXT NOT NULL,
            name TEXT NOT NULL,
            sheet_json TEXT NOT NULL DEFAULT '{}'
        );
    """,
    Domain.CHRONICLES: """
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            room_id TEXT NOT NULL,
            actor_id TEXT,
            kind TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS events_room_time ON events(room_id, created_at);
    """,
    Domain.MEMORY: """
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            room_id TEXT NOT NULL,
            source_event_id TEXT,
            content TEXT NOT NULL,
            importance REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS nodes_room_time ON nodes(room_id, created_at);
    """,
}


class SqliteStorage:
    """Own the four domain files and their connection settings."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def path_for(self, domain: Domain) -> Path:
        """Return the file for a domain."""
        return self.directory / f"{domain.value}.db"

    @contextmanager
    def connect(self, domain: Domain) -> Iterator[sqlite3.Connection]:
        """Open a transaction and close the connection on exit."""
        connection = sqlite3.connect(self.path_for(domain), timeout=10)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 10000")
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create domain databases and the first schema version."""
        self.directory.mkdir(parents=True, exist_ok=True)
        for domain, schema in SCHEMAS.items():
            with self.connect(domain) as connection:
                connection.execute("PRAGMA journal_mode = WAL")
                connection.executescript(schema)
                connection.execute("PRAGMA user_version = 1")

    def is_ready(self) -> bool:
        """Check that every domain can be read."""
        for domain in Domain:
            if not self.path_for(domain).is_file():
                return False
            with self.connect(domain) as connection:
                if connection.execute("PRAGMA user_version").fetchone()[0] != 1:
                    return False
        return True
