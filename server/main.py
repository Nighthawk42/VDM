# server/main.py
import base64
import asyncio
from pathlib import Path
from typing import Dict, List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketState

from .config import settings
from .models import (
    Room,
    WSIncomingMessage,
    WSOutgoingMessage,
    RegisterRequest,
    Player,
    LoginRequest,
)
from .room_manager import RoomManager
from .story_manager import StoryManager
from .audio_manager import AudioManager
from .game_manager import DiceRoller
from .logger import logger
from .user_manager import UserManager

# ===================================================================
# Application Setup
# ===================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
app = FastAPI(title="VDM - Virtual Dungeon Master")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "web"), name="static")

# FIX: Updated to use the new setting path from the reorganized config.
app.mount("/audio", StaticFiles(directory=Path(settings.paths.audio_out_dir)), name="audio")


class ConnectionManager:
    """Manages active WebSocket connections for each room."""

    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        self.connections.setdefault(room_id, set()).add(websocket)
        logger.info(
            f"New connection in room '{room_id}'. Total: {len(self.connections[room_id])}"
        )

    def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.connections:
            self.connections[room_id].discard(websocket)
            logger.info(
                f"Disconnected from room '{room_id}'. Remaining: {len(self.connections.get(room_id, set()))}"
            )

    async def broadcast(self, room_id: str, message: WSOutgoingMessage):
        if room_id not in self.connections:
            return
        payload = message.model_dump_json()
        tasks = [
            connection.send_text(payload)
            for connection in self.connections.get(room_id, set())
            if connection.client_state == WebSocketState.CONNECTED
        ]
        await asyncio.gather(*tasks)


# --- Instantiate Managers ---
user_manager = UserManager()
room_manager = RoomManager(user_manager=user_manager)
story_manager = StoryManager()
audio_manager = AudioManager()
game_manager = DiceRoller()
connection_manager = ConnectionManager()


# ===================================================================
# Core Game Loop Logic
# ===================================================================


async def _start_game_setup_turn(room_id: str):
    """
    Handles the very first turn of the game (the GM's setup prompt),
    respecting the streaming setting.
    """
    room_manager.get_or_create_room(room_id)

    if settings.audio.enable_streaming:
        await connection_manager.broadcast(
            room_id, WSOutgoingMessage(kind="stream_start", payload={})
        )

        full_gm_response = ""
        text_generator = story_manager.generate_gm_response_stream(room_id, [])

        async for text_chunk in text_generator:
            if not text_chunk:
                continue
            full_gm_response += text_chunk

            await connection_manager.broadcast(
                room_id, WSOutgoingMessage(kind="chat_chunk", payload={"content": text_chunk})
            )

            audio_generator = audio_manager.synthesize_stream(text_chunk)
            async for audio_chunk in audio_generator:
                encoded_chunk = base64.b64encode(audio_chunk).decode("utf-8")
                await connection_manager.broadcast(
                    room_id,
                    WSOutgoingMessage(kind="audio_chunk", payload={"chunk": encoded_chunk}),
                )

        gm_message = room_manager.add_message(
            room_id, "gm", "GM", full_gm_response.strip(), audio_url=None
        )
        await connection_manager.broadcast(
            room_id,
            WSOutgoingMessage(kind="stream_end", payload={"final_message": gm_message.model_dump()}),
        )
    else:
        gm_prompt = await story_manager.generate_gm_response(room_id, [])
        audio_url = await audio_manager.synthesize(gm_prompt)
        gm_message = room_manager.add_message(
            room_id, "gm", "GM", gm_prompt, audio_url=audio_url
        )
        await connection_manager.broadcast(
            room_id, WSOutgoingMessage(kind="chat", payload=gm_message.model_dump())
        )
        if audio_url:
            await connection_manager.broadcast(
                room_id, WSOutgoingMessage(kind="audio", payload={"url": audio_url})
            )


async def _advance_turn(room_id: str, submitter: Player):
    """
    Orchestrates the GM's turn, handling both streaming and non-streaming modes.
    """
    room_state = room_manager.get_room(room_id)
    if (
        not room_state
        or room_state.turn_state == "GM_PROCESSING"
        or not room_state.current_turn_actions
    ):
        return

    room_state.turn_state = "GM_PROCESSING"
    await connection_manager.broadcast(
        room_id,
        WSOutgoingMessage(
            kind="system",
            payload={"message": f"{submitter.name} submitted the turn. The GM ponders..."},
        ),
    )
    await connection_manager.broadcast(
        room_id, WSOutgoingMessage(kind="state_update", payload=room_state.model_dump())
    )

    turn_actions = {
        room_state.players[pid].name: action
        for pid, action in room_state.current_turn_actions.items()
        if pid in room_state.players
    }
    history = [msg.model_dump() for msg in room_state.messages]
    consolidated_actions_text = "\n".join(
        f"[{name}] {action}" for name, action in turn_actions.items()
    )
    room_manager.add_message(room_id, "party", "Party Actions", consolidated_actions_text)

    if settings.audio.enable_streaming:
        await _advance_turn_streaming(room_id, history, turn_actions)
    else:
        await _advance_turn_non_streaming(room_id, history, turn_actions)

    room_state.current_turn_actions.clear()
    room_state.turn_state = "WAITING_FOR_ACTIONS"
    await connection_manager.broadcast(
        room_id, WSOutgoingMessage(kind="state_update", payload=room_state.model_dump())
    )


async def _advance_turn_streaming(
    room_id: str, history: List[Dict], turn_actions: Dict[str, str]
):
    """Handles the game turn with real-time streaming of text and audio."""
    logger.info(f"Advancing turn for room '{room_id}' with STREAMING.")

    await connection_manager.broadcast(
        room_id, WSOutgoingMessage(kind="stream_start", payload={})
    )

    full_gm_response = ""
    text_generator = story_manager.generate_gm_response_stream(
        room_id, history, turn_actions
    )

    async for text_chunk in text_generator:
        if not text_chunk:
            continue
        full_gm_response += text_chunk

        await connection_manager.broadcast(
            room_id, WSOutgoingMessage(kind="chat_chunk", payload={"content": text_chunk})
        )

        audio_generator = audio_manager.synthesize_stream(text_chunk)
        async for audio_chunk in audio_generator:
            encoded_chunk = base64.b64encode(audio_chunk).decode("utf-8")
            await connection_manager.broadcast(
                room_id, WSOutgoingMessage(kind="audio_chunk", payload={"chunk": encoded_chunk})
            )

    gm_message = room_manager.add_message(
        room_id, "gm", "GM", full_gm_response.strip(), audio_url=None
    )
    await connection_manager.broadcast(
        room_id,
        WSOutgoingMessage(kind="stream_end", payload={"final_message": gm_message.model_dump()}),
    )


async def _advance_turn_non_streaming(
    room_id: str, history: List[Dict], turn_actions: Dict[str, str]
):
    """Handles the game turn by generating the full response before sending."""
    logger.info(f"Advancing turn for room '{room_id}' NON-STREAMING.")

    gm_response = await story_manager.generate_gm_response(
        room_id, history, turn_actions
    )
    audio_url = await audio_manager.synthesize(gm_response)
    gm_message = room_manager.add_message(
        room_id, "gm", "GM", gm_response, audio_url=audio_url
    )

    await connection_manager.broadcast(
        room_id, WSOutgoingMessage(kind="chat", payload=gm_message.model_dump())
    )
    if audio_url:
        await connection_manager.broadcast(
            room_id, WSOutgoingMessage(kind="audio", payload={"url": audio_url})
        )


async def _resume_game_turn(room_id: str, player: Player):
    """Resumes a game non-streamed for simplicity."""
    room_state = room_manager.get_room(room_id)
    if (
        not room_state
        or player.id != room_state.host_player_id
        or room_state.game_state != "PLAYING"
    ):
        return

    await connection_manager.broadcast(
        room_id,
        WSOutgoingMessage(kind="system", payload={"message": f"{player.name} is resuming the game..."}),
    )
    room_state.turn_state = "GM_PROCESSING"
    await connection_manager.broadcast(
        room_id, WSOutgoingMessage(kind="state_update", payload=room_state.model_dump())
    )

    history = [msg.model_dump() for msg in room_state.messages]
    gm_summary = await story_manager.generate_resume_summary(room_id, history)
    audio_url = await audio_manager.synthesize(gm_summary)
    gm_message = room_manager.add_message(
        room_id, "gm", "GM", gm_summary, audio_url=audio_url
    )

    await connection_manager.broadcast(
        room_id, WSOutgoingMessage(kind="chat", payload=gm_message.model_dump())
    )
    if audio_url:
        await connection_manager.broadcast(
            room_id, WSOutgoingMessage(kind="audio", payload={"url": audio_url})
        )

    room_state.turn_state = "WAITING_FOR_ACTIONS"
    await connection_manager.broadcast(
        room_id, WSOutgoingMessage(kind="state_update", payload=room_state.model_dump())
    )


# ===================================================================
# API & WebSocket Endpoints
# ===================================================================


@app.get("/")
async def get_root():
    return FileResponse(BASE_DIR / "web/index.html")


@app.post("/api/register")
async def register_player(request: RegisterRequest):
    success, message = user_manager.register_player(
        request.name, request.avatar_style, request.password
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return JSONResponse(content={"message": message})


@app.post("/api/login")
async def login_player(request: LoginRequest):
    user_data = user_manager.login(request.name, request.password)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return JSONResponse(content=user_data)


@app.get("/api/voices")
async def get_voices():
    return JSONResponse(content=audio_manager.list_voices())


@app.websocket("/ws/{room_id}/{player_id}/{player_token}")
async def websocket_endpoint(
    websocket: WebSocket, room_id: str, player_id: str, player_token: str
):
    add_player_result = room_manager.add_player(room_id, player_id, player_token)
    if not add_player_result:
        await websocket.close(code=4001, reason="Invalid session token.")
        return

    await connection_manager.connect(room_id, websocket)
    room, player = add_player_result

    if not room.host_player_id:
        room.host_player_id = player_id
        logger.info(f"Player '{player.name}' is now the host of room '{room_id}'.")

    await connection_manager.broadcast(
        room_id,
        WSOutgoingMessage(kind="system", payload={"message": f"{player.name} has joined the game!"}),
    )
    await connection_manager.broadcast(
        room_id, WSOutgoingMessage(kind="state_update", payload=room.model_dump())
    )

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = WSIncomingMessage.model_validate_json(data)
                room_state = room_manager.get_room(room_id)
                if not room_state:
                    continue

                if msg.kind == "start_game":
                    if (
                        player.id == room_state.host_player_id
                        and room_state.game_state == "LOBBY"
                    ):
                        room_state.game_state = "PLAYING"
                        
                        await connection_manager.broadcast(
                            room_id,
                            WSOutgoingMessage(
                                kind="system", payload={"message": "The game is starting..."}
                            ),
                        )
                        await _start_game_setup_turn(room_id)

                        await connection_manager.broadcast(
                            room_id,
                            WSOutgoingMessage(
                                kind="state_update", payload=room_state.model_dump()
                            ),
                        )

                elif msg.kind == "resume_game":
                    await _resume_game_turn(room_id, player)

                elif msg.kind == "submit_turn":
                    await _advance_turn(room_id, player)

                elif msg.kind == "say":
                    text = msg.payload.get("message", "").strip()
                    if not text:
                        continue

                    is_command = text.startswith("/")
                    if is_command:
                        parts = text.split()
                        cmd = parts[0].lower()
                        if cmd == "/roll":
                            notation = parts[1] if len(parts) > 1 else "1d20"
                            result = game_manager.roll(notation)
                            if result:
                                roll_msg = room_manager.add_message(
                                    room_id,
                                    player.id,
                                    player.name,
                                    f"rolls {result.as_string}",
                                )
                                await connection_manager.broadcast(
                                    room_id,
                                    WSOutgoingMessage(
                                        kind="chat",
                                        payload={
                                            **roll_msg.model_dump(),
                                            "is_roll": True,
                                        },
                                    ),
                                )
                        elif cmd == "/save":
                            room_manager.save_room_state(room_id)
                            await connection_manager.broadcast(
                                room_id,
                                WSOutgoingMessage(
                                    kind="system",
                                    payload={
                                        "message": f"Game progress saved by {player.name}."
                                    },
                                ),
                            )
                        elif cmd == "/remember":
                            memory_text = " ".join(parts[1:])
                            if memory_text:
                                story_manager.memory_manager.add_memory(
                                    room_id, memory_text
                                )
                                await connection_manager.broadcast(
                                    room_id,
                                    WSOutgoingMessage(
                                        kind="system",
                                        payload={
                                            "message": f"{player.name} added a memory: '{memory_text[:50]}...'"
                                        },
                                    ),
                                )
                        elif cmd == "/next":
                            await _advance_turn(room_id, player)
                        elif cmd == "/ooc":
                            ooc_text = " ".join(parts[1:])
                            if ooc_text:
                                ooc_msg = room_manager.add_message(
                                    room_id, player.id, player.name, f"// {ooc_text}"
                                )
                                await connection_manager.broadcast(
                                    room_id,
                                    WSOutgoingMessage(
                                        kind="chat",
                                        payload={
                                            **ooc_msg.model_dump(),
                                            "is_ooc": True,
                                        },
                                    ),
                                )
                        else:
                            await websocket.send_text(
                                WSOutgoingMessage(
                                    kind="system",
                                    payload={"message": f"Unknown command: {cmd}"},
                                ).model_dump_json()
                            )
                    else:
                        if room_state.turn_state == "GM_PROCESSING":
                            continue
                        room_state.current_turn_actions[player.id] = text
                        action_msg = room_manager.add_message(
                            room_id, player.id, player.name, text
                        )
                        await connection_manager.broadcast(
                            room_id,
                            WSOutgoingMessage(
                                kind="chat", payload=action_msg.model_dump()
                            ),
                        )
                        await connection_manager.broadcast(
                            room_id,
                            WSOutgoingMessage(
                                kind="state_update", payload=room_state.model_dump()
                            ),
                        )
            except Exception:
                logger.error(f"Error processing message from {player.name}", exc_info=True)

    except WebSocketDisconnect:
        user_manager.logout(player_token)
        connection_manager.disconnect(room_id, websocket)
        disconnected_player = room_manager.remove_player(room_id, player_id)
        if disconnected_player and (room_state := room_manager.get_room(room_id)):
            room_state.current_turn_actions.pop(player_id, None)
            if room_state.host_player_id == player_id:
                new_host_id = next(
                    (pid for pid, p in room_state.players.items() if p.is_active), None
                )
                room_state.host_player_id = new_host_id
                if new_host_id:
                    new_host_name = room_state.players[new_host_id].name
                    await connection_manager.broadcast(
                        room_id,
                        WSOutgoingMessage(
                            kind="system",
                            payload={
                                "message": f"The host has left. {new_host_name} is the new host."
                            },
                        ),
                    )
            await connection_manager.broadcast(
                room_id,
                WSOutgoingMessage(
                    kind="system",
                    payload={"message": f"{disconnected_player.name} has left the game."},
                ),
            )
            await connection_manager.broadcast(
                room_id,
                WSOutgoingMessage(kind="state_update", payload=room_state.model_dump()),
            )