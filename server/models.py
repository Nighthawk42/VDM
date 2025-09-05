# server/models.py
from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Any, Optional

# ===================================================================
# Core Game & Application Models
# ===================================================================
# These Pydantic models define the structure of our application's state.

class Player(BaseModel):
    id: str
    name: str
    avatar_style: str = "adventurer"
    is_active: bool = True

class ChatMessage(BaseModel):
    author_id: str
    author_name: str
    content: str
    audio_url: Optional[str] = None
    is_ooc: bool = False

class Room(BaseModel):
    room_id: str
    players: Dict[str, Player] = Field(default_factory=dict)
    messages: List[ChatMessage] = Field(default_factory=list)
    turn_state: Literal["WAITING_FOR_ACTIONS", "GM_PROCESSING"] = "WAITING_FOR_ACTIONS"
    current_turn_actions: Dict[str, str] = Field(default_factory=dict)
    game_state: Literal["LOBBY", "PLAYING"] = "LOBBY"
    host_player_id: Optional[str] = None

class RegisterRequest(BaseModel):
    name: str
    avatar_style: str
    password: str

class LoginRequest(BaseModel):
    name: str
    password: str

# ===================================================================
# WebSocket Protocol Models
# ===================================================================
# These models define the contract for messages sent between the
# server and the clients over the WebSocket connection.

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
        "stream_end"
    ]
    payload: Dict[str, Any]