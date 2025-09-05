# server/room_manager.py
from typing import Dict, Optional, Tuple

from .models import Room, Player, ChatMessage
from .logger import logger
# REMOVED: from .persistence_manager import PersistenceManager
from .user_manager import UserManager

class RoomManager:
    """Manages the state of all active VDM rooms in memory."""

    def __init__(self, user_manager: UserManager):
        """Initializes the RoomManager with its dependencies."""
        from .persistence_manager import PersistenceManager # <-- FIX: Import moved inside __init__
        
        self._rooms: Dict[str, Room] = {}
        self._persistence_manager = PersistenceManager()
        self._user_manager = user_manager

    def get_or_create_room(self, room_id: str) -> Room:
        """
        Retrieves a room by its ID, loading from a session file if available.
        """
        if room_id in self._rooms:
            return self._rooms[room_id]

        loaded_room = self._persistence_manager.load_room(room_id)
        if loaded_room:
            for player in loaded_room.players.values():
                player.is_active = False
            self._rooms[room_id] = loaded_room
            return loaded_room

        logger.info(f"Creating new room '{room_id}'")
        new_room = Room(room_id=room_id)
        self._rooms[room_id] = new_room
        return new_room

    def save_room_state(self, room_id: str):
        """A convenience method to trigger saving a room's state."""
        if room_id in self._rooms:
            self._persistence_manager.save_room(self._rooms[room_id])
        else:
            logger.warning(f"Attempted to save non-existent or inactive room: {room_id}")

    def add_player(self, room_id: str, player_id: str, player_token: str) -> Optional[Tuple[Room, Player]]:
        """
        Adds or reactivates a player in a room using their auth token.
        """
        player_data = self._user_manager.get_user_by_token(player_token)
        if not player_data:
            logger.warning(f"Player with invalid token tried to join room '{room_id}'.")
            return None

        room = self.get_or_create_room(room_id)
        player_name = player_data["name"]

        existing_player: Optional[Player] = None
        old_player_id: Optional[str] = None
        for pid, p in room.players.items():
            if p.name.lower() == player_name.lower():
                existing_player = p
                old_player_id = pid
                break

        if existing_player:
            if existing_player.is_active:
                logger.warning(f"Player '{player_name}' tried to join room '{room_id}' but is already active.")
                # Allow rejoining for simplicity, just update their ID.
                # This handles cases where a client disconnects without the server knowing.
            
            logger.info(f"Player '{player_name}' is reconnecting to room '{room_id}'.")
            if old_player_id and old_player_id in room.players:
                # Remove the old entry if the client ID has changed (e.g., new browser tab)
                if old_player_id != player_id:
                    del room.players[old_player_id]
            
            existing_player.id = player_id
            existing_player.is_active = True
            existing_player.avatar_style = player_data["avatar_style"]
            room.players[player_id] = existing_player
            return room, existing_player
        
        logger.info(f"Player '{player_name}' ({player_id}) joined room '{room_id}' for the first time.")
        new_player = Player(
            id=player_id, 
            name=player_data["name"], 
            avatar_style=player_data["avatar_style"],
            is_active=True
        )
        room.players[player_id] = new_player
        return room, new_player

    def remove_player(self, room_id: str, player_id: str) -> Optional[Player]:
        """
        Deactivates a player in a room, preserving their data.
        """
        room = self._rooms.get(room_id)
        if room and player_id in room.players:
            player = room.players[player_id]
            player.is_active = False
            logger.info(f"Player '{player.name}' ({player_id}) disconnected from room '{room_id}'.")
            if not any(p.is_active for p in room.players.values()):
                logger.info(f"Last active player left room '{room_id}'. Saving state.")
                self.save_room_state(room_id)
            return player
        return None

    def add_message(
        self, 
        room_id: str, 
        author_id: str, 
        author_name: str, 
        content: str, 
        audio_url: Optional[str] = None
    ) -> ChatMessage:
        """
        Adds a chat message to a room's history, optionally with an audio URL.
        """
        room = self.get_or_create_room(room_id)
        message = ChatMessage(
            author_id=author_id, 
            author_name=author_name, 
            content=content, 
            audio_url=audio_url
        )
        room.messages.append(message)
        return message
    
    def get_room(self, room_id: str) -> Optional[Room]:
        """
        Safely retrieves an active room's state from memory.
        """
        return self._rooms.get(room_id)