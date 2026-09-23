"""Password based identity and opaque, revocable browser sessions."""

import hashlib
import secrets
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from vdm.storage.sqlite import Domain, SqliteStorage

SESSION_DAYS = 30


@dataclass(frozen=True)
class User:
    """The public identity fields needed by API routes."""

    id: str
    username: str
    is_admin: bool


class AuthService:
    """Create users and store only digests of random session tokens."""

    def __init__(self, storage: SqliteStorage) -> None:
        self.storage = storage
        self.hasher = PasswordHasher()

    def register(self, username: str, password: str) -> User:
        """Create an account, raising ``ValueError`` for a taken username."""
        user = User(id=uuid.uuid4().hex, username=username, is_admin=False)
        password_hash = self.hasher.hash(password)
        try:
            with self.storage.connect(Domain.AUTH) as connection:
                connection.execute(
                    "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
                    (user.id, user.username, password_hash),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Username is already registered") from exc
        return user

    def login(self, username: str, password: str) -> tuple[User, str] | None:
        """Verify a password and return the user plus a new bearer cookie value."""
        with self.storage.connect(Domain.AUTH) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT id, username, password_hash, is_admin FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if row is None:
                return None
            try:
                self.hasher.verify(row["password_hash"], password)
            except (VerifyMismatchError, VerificationError, InvalidHashError):
                return None
            if self.hasher.check_needs_rehash(row["password_hash"]):
                connection.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (self.hasher.hash(password), row["id"]),
                )
            token = secrets.token_urlsafe(32)
            expires_at = (datetime.now(UTC) + timedelta(days=SESSION_DAYS)).isoformat()
            connection.execute(
                "INSERT INTO sessions (id, user_id, expires_at) VALUES (?, ?, ?)",
                (self._digest(token), row["id"], expires_at),
            )
        return User(row["id"], row["username"], bool(row["is_admin"])), token

    def authenticate(self, token: str | None) -> User | None:
        """Find an unexpired session without exposing its stored digest."""
        if not token:
            return None
        with self.storage.connect(Domain.AUTH) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """SELECT u.id, u.username, u.is_admin FROM sessions AS s
                   JOIN users AS u ON u.id = s.user_id
                   WHERE s.id = ? AND s.expires_at > ?""",
                (self._digest(token), datetime.now(UTC).isoformat()),
            ).fetchone()
        if row is None:
            return None
        return User(row["id"], row["username"], bool(row["is_admin"]))

    def logout(self, token: str | None) -> None:
        """Revoke a session if present."""
        if token:
            with self.storage.connect(Domain.AUTH) as connection:
                connection.execute("DELETE FROM sessions WHERE id = ?", (self._digest(token),))

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
