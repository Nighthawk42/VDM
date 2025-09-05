# server/persistence_manager.py
from pathlib import Path
from typing import Optional

from .config import settings
from .logger import logger
from .models import Room
from .database_manager import DatabaseManager

class PersistenceManager:
    """Handles saving and loading of room session states via the DatabaseManager."""

    def __init__(self):
        """Initializes the manager and sets up the database connection."""
        db_path = Path(settings.memory.database_file)
        self.db_manager = DatabaseManager(db_path)
        logger.info(f"Persistence manager is now using the database backend.")

    def save_room(self, room: Room) -> bool:
        """
        Saves the complete state of a room to the database.

        Args:
            room: The Room object to save.

        Returns:
            True if saving was successful, False otherwise.
        """
        logger.info(f"Saving session for room '{room.room_id}'...")
        return self.db_manager.save_room(room)

    def load_room(self, room_id: str) -> Optional[Room]:
        """
        Loads a room's state from the database if it exists.

        Args:
            room_id: The ID of the room to load.

        Returns:
            A Room object if a session was found and loaded successfully, otherwise None.
        """
        logger.info(f"Attempting to load session for room '{room_id}'...")
        return self.db_manager.load_room(room_id)