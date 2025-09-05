# server/room_manager.py
from typing import Dict, Optional, Tuple

from .models import Room, Player, ChatMessage
from .logger import logger
from .user_manager import UserManager
from .persistence_manager import PersistenceManager

class RoomManager:
    """Manages the state of all active VDM rooms in memory."""

    def __init__(self, user_manager: UserManager, persistence_manager: PersistenceManager):
        """
        Initializes the RoomManager with its dependencies.

        Args:
            user_manager: An active instance of the UserManager.
            persistence_manager: An active instance of the PersistenceManager.
        """
        self._rooms: Dict[str, Room] = {}
        self._persistence_manager = persistence_manager
        self._user_manager = user_manager

    def get_or_create_room(self, room_id: str) -> Room:
        """
        Retrieves a room by its ID from memory, or loads it from persistence.
        If not found, a new empty room is created.

        Args:
            room_id: The unique identifier for the room.

        Returns:
            The active Room object.
        """
        if room_id in self._rooms:
            return self._rooms[room_id]

        loaded_room = self._persistence_manager.load_room(room_id)
        if loaded_room:
            # When loading a room, mark all players as inactive until they reconnect.
            for player in loaded_room.players.values():
                player.is_active = False
            self._rooms[room_id] = loaded_room
            return loaded_room

        logger.info(f"Creating new room '{room_id}'")
        new_room = Room(room_id=room_id)
        self._rooms[room_id] = new_room
        return new_room

    def save_room_state(self, room_id: str):
        """A convenience method to trigger saving a room's state via the persistence manager."""
        if room_id in self._rooms:
            self._persistence_manager.save_room(self._rooms[room_id])
        else:
            logger.warning(f"Attempted to save non-existent or inactive room: {room_id}")

    def add_player(self, room_id: str, player_id: str, player_token: str) -> Optional[Tuple[Room, Player]]:
        """
        Adds a player to a room or reactivates them if they are rejoining.
        Validates the player's session token.

        Args:
            room_id: The ID of the room to join.
            player_id: The client-generated unique ID for the player's connection.
            player_token: The session token obtained during login.

        Returns:
            A tuple of (Room, Player) if successful, otherwise None.
        """
        player_data = self._user_manager.get_user_by_token(player_token)
        if not player_data:
            logger.warning(f"Player with invalid token tried to join room '{room_id}'.")
            return None

        room = self.get_or_create_room(room_id)
        player_name = player_data["username_cased"] # Use the cased name from DB

        # Check if this player (by name) is already in the room state
        existing_player: Optional[Player] = None
        for p in room.players.values():
            if p.name.lower() == player_name.lower():
                existing_player = p
                break
        
        if existing_player:
            logger.info(f"Player '{player_name}' is reconnecting to room '{room_id}'.")
            existing_player.is_active = True
            # Update ID and avatar in case they changed or are logging in from a new client
            existing_player.id = player_id 
            existing_player.avatar_style = player_data["avatar_style"]
            return room, existing_player
        
        logger.info(f"Player '{player_name}' ({player_id}) joined room '{room_id}' for the first time.")
        new_player = Player(
            id=player_id, 
            name=player_name, 
            avatar_style=player_data["avatar_style"],
            is_active=True
        )
        room.players[player_id] = new_player
        return room, new_player

    def remove_player(self, room_id: str, player_id: str) -> Optional[Player]:
        """
        Deactivates a player in a room, preserving their data for reconnection.
        If the last active player leaves, the room state is saved.

        Args:
            room_id: The ID of the room the player is leaving.
            player_id: The ID of the player's connection.

        Returns:
            The Player object that was deactivated, or None if not found.
        """
        room = self._rooms.get(room_id)
        if room and player_id in room.players:
            player = room.players[player_id]
            player.is_active = False
            logger.info(f"Player '{player.name}' ({player_id}) disconnected from room '{room_id}'.")
            
            # If this was the last active player, save the game state.
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
        Adds a chat message to a room's history.

        Returns:
            The created ChatMessage object.
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