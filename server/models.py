# server/models.py
from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Any, Optional

# ===================================================================
# Core Game & Application Models
# ===================================================================

class Player(BaseModel):
    """Represents a player within a game room."""
    id: str
    name: str
    avatar_style: str = "adventurer"
    is_active: bool = True
    # REMOVED: The 'sheet' attribute has been removed from the Player model.


class ChatMessage(BaseModel):
    """Represents a single message in the chat history."""
    author_id: str
    author_name: str
    content: str
    audio_url: Optional[str] = None
    is_ooc: bool = False

class Room(BaseModel):
    """Represents the entire state of a single game room."""
    room_id: str
    players: Dict[str, Player] = Field(default_factory=dict)
    messages: List[ChatMessage] = Field(default_factory=list)
    turn_state: Literal["WAITING_FOR_ACTIONS", "GM_PROCESSING"] = "WAITING_FOR_ACTIONS"
    current_turn_actions: Dict[str, str] = Field(default_factory=dict)
    game_state: Literal["LOBBY", "PLAYING"] = "LOBBY"
    host_player_id: Optional[str] = None
    owner_username: Optional[str] = None

class RegisterRequest(BaseModel):
    """Model for the /api/register endpoint payload."""
    name: str
    avatar_style: str
    password: str

class LoginRequest(BaseModel):
    """Model for the /api/login endpoint payload."""
    name: str
    password: str

# ===================================================================
# WebSocket Protocol Models
# ===================================================================

class WSIncomingMessage(BaseModel):
    """A message received from a client."""
    kind: Literal[
        "say",
        "start_game",
        "submit_turn",
        "resume_game"
    ]
    payload: Dict[str, Any]

class WSOutgoingMessage(BaseModel):
    """A message sent from the server to clients."""
    kind: Literal[
        "system",
        "chat",
        "audio",
        "state_update",
        "stream_start",
        "chat_chunk",
        "audio_chunk",
        "stream_end",
        "chat_history"
    ]
    payload: Dict[str, Any]