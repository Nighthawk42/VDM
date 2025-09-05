# server/database_manager.py
import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, Any

from .models import Room
from .logger import logger

class DatabaseManager:
    """
    Handles all direct SQLite database operations for VDM, managing separate
    databases for session/room data and user/account data.
    """

    def __init__(self, sessions_db_path: Path, users_db_path: Path):
        """
        Initializes connections to both the sessions and users databases.
        It creates the databases and their respective tables if they don't exist.
        """
        self.sessions_db_path = sessions_db_path
        self.users_db_path = users_db_path
        self.sessions_conn: Optional[sqlite3.Connection] = None
        self.users_conn: Optional[sqlite3.Connection] = None

        try:
            # Connect to the sessions database
            self.sessions_db_path.parent.mkdir(parents=True, exist_ok=True)
            self.sessions_conn = sqlite3.connect(self.sessions_db_path, check_same_thread=False)
            logger.info(f"Connected to sessions database at '{self.sessions_db_path}'.")
            self._create_rooms_table()

            # Connect to the users database
            self.users_db_path.parent.mkdir(parents=True, exist_ok=True)
            self.users_conn = sqlite3.connect(self.users_db_path, check_same_thread=False)
            self.users_conn.row_factory = sqlite3.Row # Use Row factory for dict-like user results
            logger.info(f"Connected to users database at '{self.users_db_path}'.")
            self._create_users_table()

        except sqlite3.Error as e:
            logger.critical(f"Database connection failed: {e}", exc_info=True)
            raise

    def _create_rooms_table(self):
        """Creates the 'rooms' table in the sessions database if it's not present."""
        if not self.sessions_conn: return
        try:
            cursor = self.sessions_conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rooms (
                    room_id TEXT PRIMARY KEY,
                    room_data TEXT NOT NULL
                )
            """)
            self.sessions_conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to create 'rooms' table: {e}", exc_info=True)

    def _create_users_table(self):
        """Creates the 'users' table in the users database if it's not present."""
        if not self.users_conn: return
        try:
            cursor = self.users_conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username_lower TEXT PRIMARY KEY,
                    username_cased TEXT NOT NULL UNIQUE,
                    hashed_password TEXT NOT NULL,
                    avatar_style TEXT NOT NULL
                )
            """)
            self.users_conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to create 'users' table: {e}", exc_info=True)

    # --- User Management Methods (Uses users_conn) ---

    def add_user(self, username: str, hashed_password: str, avatar_style: str) -> bool:
        """Adds a new user to the users database."""
        if not self.users_conn: return False
        try:
            cursor = self.users_conn.cursor()
            cursor.execute(
                "INSERT INTO users (username_lower, username_cased, hashed_password, avatar_style) VALUES (?, ?, ?, ?)",
                (username.lower(), username, hashed_password, avatar_style)
            )
            self.users_conn.commit()
            logger.info(f"Successfully added user '{username}' to the database.")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Attempted to add a user that already exists: {username}")
            return False
        except sqlite3.Error as e:
            logger.error(f"Failed to add user '{username}' to database.", exc_info=True)
            return False

    def get_user_by_name(self, username: str) -> Optional[Dict[str, Any]]:
        """Retrieves a user's data from the users database (case-insensitive)."""
        if not self.users_conn: return None
        try:
            cursor = self.users_conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username_lower = ?", (username.lower(),))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Failed to get user '{username}' from database.", exc_info=True)
            return None

    # --- Room Management Methods (Uses sessions_conn) ---

    def save_room(self, room: Room) -> bool:
        """Saves a room's state to the sessions database."""
        if not self.sessions_conn: return False
        try:
            json_data = room.model_dump_json()
            cursor = self.sessions_conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO rooms (room_id, room_data) VALUES (?, ?)",
                (room.room_id, json_data)
            )
            self.sessions_conn.commit()
            logger.info(f"Successfully saved room '{room.room_id}' to the database.")
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to save room '{room.room_id}' to database.", exc_info=True)
            return False

    def load_room(self, room_id: str) -> Optional[Room]:
        """Loads a room's state from the sessions database."""
        if not self.sessions_conn: return None
        try:
            cursor = self.sessions_conn.cursor()
            cursor.execute("SELECT room_data FROM rooms WHERE room_id = ?", (room_id,))
            row = cursor.fetchone()
            if row:
                json_data = row[0]
                room = Room.model_validate_json(json_data)
                logger.info(f"Successfully loaded room '{room_id}' from the database.")
                return room
            else:
                logger.info(f"No database entry found for room '{room_id}'.")
                return None
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.error(f"Failed to load room '{room_id}' from database.", exc_info=True)
            return None

    def close(self):
        """Closes both database connections."""
        if self.sessions_conn:
            self.sessions_conn.close()
            logger.info("Sessions database connection closed.")
        if self.users_conn:
            self.users_conn.close()
            logger.info("Users database connection closed.")