# server/database_manager.py
import sqlite3
import json
from pathlib import Path
from typing import Optional

from .models import Room
from .logger import logger

class DatabaseManager:
    """Handles all direct SQLite database operations for VDM."""

    def __init__(self, db_path: Path):
        """
        Initializes the database connection and creates tables if they don't exist.
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            logger.info(f"Connected to SQLite database at '{self.db_path}'.")
            self._create_tables()
        except sqlite3.Error as e:
            logger.critical(f"Database connection failed: {e}", exc_info=True)
            raise

    def _create_tables(self):
        """Creates the 'rooms' table if it's not already present."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rooms (
                    room_id TEXT PRIMARY KEY,
                    room_data TEXT NOT NULL
                )
            """)
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to create database tables: {e}", exc_info=True)

    def save_room(self, room: Room) -> bool:
        """
        Saves a room's state to the database, overwriting if it exists.
        The room object is stored as a JSON string.
        """
        try:
            json_data = room.model_dump_json()
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO rooms (room_id, room_data) VALUES (?, ?)",
                (room.room_id, json_data)
            )
            self.conn.commit()
            logger.info(f"Successfully saved room '{room.room_id}' to the database.")
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to save room '{room.room_id}' to database.", exc_info=True)
            return False

    def load_room(self, room_id: str) -> Optional[Room]:
        """
        Loads a room's state from the database using its ID.
        """
        try:
            cursor = self.conn.cursor()
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
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed.")