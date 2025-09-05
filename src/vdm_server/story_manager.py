# server/story_manager.py
from __future__ import annotations

import re
import yaml
import json
from typing import List, Dict, Any, Optional, AsyncGenerator

from .config import settings
from .llm_providers import LLMProvider, make_llm_provider
from .logger import logger
from .memory_manager import MemoryManager

# ==============================================================================
# Prompt Loading & Dynamic Construction
# ==============================================================================
def load_prompts_from_yaml(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.critical(f"Prompts YAML file not found at: {path}")
        exit(1)
    except Exception as e:
        logger.critical(f"Failed to load or parse prompts YAML file: {e}", exc_info=True)
        exit(1)

PROMPTS = load_prompts_from_yaml(settings.paths.prompts_file)

VDM_SETUP_PROMPT = PROMPTS.get("setup", "")
VDM_RESUME_PROMPT = PROMPTS.get("resume_game", "")

_gameplay_prompts = PROMPTS.get("gameplay", {})
_BASE_INSTRUCTION = _gameplay_prompts.get("base", "")
_JSON_INPUT_INSTRUCTION = _gameplay_prompts.get("json_input_instruction", "")
_LEGACY_TEXT_INSTRUCTION = _gameplay_prompts.get("legacy_text_input_instruction", "")
_VOICE_TAGGING_INSTRUCTION = _gameplay_prompts.get("voice_tagging_instruction", "")
_REASONING_TAG_INSTRUCTION = _gameplay_prompts.get("tagging_instruction", "")

def build_system_prompt() -> str:
    parts = [_BASE_INSTRUCTION]
    if settings.llm.prompting_strategy == "json":
        parts.append(_JSON_INPUT_INSTRUCTION)
    else:
        parts.append(_LEGACY_TEXT_INSTRUCTION)
    if settings.audio.enable_dynamic_casting:
        parts.append(_VOICE_TAGGING_INSTRUCTION)
    if settings.llm.llm_uses_tags:
        parts.append(_REASONING_TAG_INSTRUCTION)
    return "\n\n".join(p for p in parts if p)

VDM_SYSTEM_PROMPT = build_system_prompt()
logger.info("VDM System Prompt constructed successfully.")

class StoryManager:
    def __init__(self):
        self.provider: LLMProvider = make_llm_provider()
        self.memory_manager = MemoryManager()

    # -------------------------- Parsing helpers --------------------------
    def _parse_llm_output(self, raw_text: str) -> str:
        if not settings.llm.llm_uses_tags:
            return raw_text.strip()
        match = re.search(r'<RESPONSE>(.*)</RESPONSE>', raw_text, re.DOTALL)
        if match:
            return match.group(1).strip()
        logger.warning("llm_uses_tags is true, but could not find <RESPONSE>. Using raw text.")
        return raw_text.replace("<thinking>", "").replace("</thinking>", "").strip()

    def _parse_player_input(self, text: str) -> Dict[str, str]:
        dialogue_parts = re.findall(r'["“](.*?)["”]', text)
        dialogue = " ".join(dialogue_parts).strip()
        action = re.sub(r'["“](.*?)["”]', '', text).strip()
        if not action and dialogue:
            action = "Says..."
        elif not action and not dialogue:
            action = "..."
        return {"action": action, "dialogue": dialogue}

    # ---------------------- Message shaping helpers ----------------------
    @staticmethod
    def _coalesce_same_role(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if not messages:
            return []
        out: List[Dict[str, str]] = []
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if out and out[-1]["role"] == role:
                out[-1]["content"] = (out[-1]["content"] + ("\n\n" if out[-1]["content"] else "") + content).strip()
            elif role:
                out.append({"role": role, "content": content})
        return out

    def _prepare_turn_actions_block(self, turn_actions: Dict[str, str]) -> Dict[str, str]:
        final_instruction = "Based on the above inputs and any relevant memories, generate the next part of the story."
        if settings.llm.prompting_strategy == "json":
            structured_actions = []
            for player_name, action_text in turn_actions.items():
                parsed = self._parse_player_input(action_text)
                structured_actions.append({
                    "player_name": player_name,
                    "action": parsed["action"],
                    "dialogue": parsed["dialogue"]
                })
            actions_json = json.dumps(structured_actions, indent=2)
            content = (
                "Here are the player inputs for the current turn:\n"
                f"```json\n{actions_json}\n```\n\n{final_instruction}"
            )
        else:
            action_lines = [f"[{name}]: {action}" for name, action in turn_actions.items()]
            consolidated_actions = "\n".join(action_lines)
            content = (
                "Here are the actions for the current turn:\n"
                f"{consolidated_actions}\n\n{final_instruction}"
            )
        return {"role": "user", "content": content}

    def _prepare_messages(
        self,
        room_id: str,
        chat_history: List[Dict[str, Any]],
        turn_actions: Dict[str, str]
    ) -> List[Dict[str, str]]:
        # Light memory retrieval
        query_text = " ".join([msg.get('content', '') for msg in chat_history[-5:]] + list(turn_actions.values()))
        memories = self.memory_manager.search_memory(room_id, query_text)
        memory_context = ""
        if memories:
            memory_list = "\n".join(f"- {m}" for m in memories)
            memory_context = f"\n\nHere are some relevant memories from the past:\n{memory_list}"

        system_prompt = f"{VDM_SYSTEM_PROMPT}{memory_context}"
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        # Pull in recent chat history as alternating user/assistant
        recent_history = chat_history[-settings.llm.context_messages:]
        for message in recent_history:
            role = 'assistant' if message.get('author_id') == 'gm' else 'user'
            author_id = message.get('author_id')

            # Avoid duplicating the same player inputs when we add the consolidated block
            if (role == 'user' and author_id in turn_actions) or author_id == 'party':
                continue

            content = message.get('content', '')
            if role == 'user':
                author_name = message.get('author_name', 'Player')
                content = f"[{author_name}]: {content}"
            if content.strip():
                messages.append({"role": role, "content": content})

        # Consolidated actions for this turn (as a single user block)
        if turn_actions:
            messages.append(self._prepare_turn_actions_block(turn_actions))

        # Only coalesce; do NOT force-add a trailing user (LM Studio will add model turn itself)
        messages = self._coalesce_same_role(messages)
        return messages

    # ----------------------------- Public API ----------------------------
    async def generate_gm_response(
        self,
        room_id: str,
        chat_history: List[Dict[str, Any]],
        turn_actions: Optional[Dict[str, str]] = None
    ) -> str:
        if not chat_history:
            messages = [
                {"role": "system", "content": VDM_SETUP_PROMPT},
                {"role": "user", "content": "Begin the game by greeting the players and asking about the setting."}
            ]
            messages = self._coalesce_same_role(messages)
            raw_response = await self.provider.generate_completion_non_stream(messages)
            return self._parse_llm_output(raw_response)

        if len(chat_history) == 1 and chat_history[0].get('author_id') != 'gm':
            player_idea = f"[{chat_history[0].get('author_name', 'Player')}]: {chat_history[0].get('content', '')}"
            messages = [
                {"role": "system", "content": VDM_SYSTEM_PROMPT},
                {"role": "user", "content": f"The players have decided on the following setting: {player_idea}. Generate a compelling opening scene and ask what they do."}
            ]
            messages = self._coalesce_same_role(messages)
            raw_response = await self.provider.generate_completion_non_stream(messages)
            parsed_response = self._parse_llm_output(raw_response)
            self.memory_manager.add_memory(room_id, f"The game's setting is: {chat_history[0].get('content', '')}")
            return parsed_response

        active_turn_actions = turn_actions or {}
        messages = self._prepare_messages(room_id, chat_history, active_turn_actions)
        raw_response = await self.provider.generate_completion_non_stream(messages)
        parsed_response = self._parse_llm_output(raw_response)

        if parsed_response and active_turn_actions:
            turn_summary = "Players did: " + ". ".join(active_turn_actions.values()) + ". Result: " + parsed_response
            self.memory_manager.add_memory(room_id, turn_summary)
        return parsed_response

    async def generate_gm_response_stream(
        self,
        room_id: str,
        chat_history: List[Dict[str, Any]],
        turn_actions: Optional[Dict[str, str]] = None
    ) -> AsyncGenerator[str, None]:
        if not chat_history:
            messages = [
                {"role": "system", "content": VDM_SETUP_PROMPT},
                {"role": "user", "content": "Begin the game by greeting the players and asking about the setting."}
            ]
        elif len(chat_history) == 1 and chat_history[0].get('author_id') != 'gm':
            player_idea = f"[{chat_history[0].get('author_name', 'Player')}]: {chat_history[0].get('content', '')}"
            messages = [
                {"role": "system", "content": VDM_SYSTEM_PROMPT},
                {"role": "user", "content": f"The players have decided on the following setting: {player_idea}. Generate a compelling opening scene and ask what they do."}
            ]
            self.memory_manager.add_memory(room_id, f"The game's setting is: {chat_history[0].get('content', '')}")
        else:
            active_turn_actions = turn_actions or {}
            messages = self._prepare_messages(room_id, chat_history, active_turn_actions)

        # Coalesce only
        messages = self._coalesce_same_role(messages)

        full_response = ""
        async for chunk in self.provider.generate_completion_stream(messages):
            yield chunk
            full_response += chunk

        if turn_actions and full_response.strip():
            turn_summary = "Players did: " + ". ".join(turn_actions.values()) + ". Result: " + full_response.strip()
            self.memory_manager.add_memory(room_id, turn_summary)

    async def generate_resume_summary(self, room_id: str, chat_history: List[Dict[str, Any]]) -> str:
        logger.info(f"Generating resume summary for room '{room_id}'...")
        if not chat_history:
            return "There is no game history to resume from."

        query_text = " ".join([msg.get('content', '') for msg in chat_history[-10:]])
        memories = self.memory_manager.search_memory(room_id, query_text, k=5)
        memory_context = ""
        if memories:
            memory_list = "\n".join(f"- {m}" for m in memories)
            memory_context = f"\n\nHere are some relevant memories from the past:\n{memory_list}"

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": f"{VDM_RESUME_PROMPT}{memory_context}"}
        ]
        recent_history = chat_history[-settings.llm.context_messages:]
        for message in recent_history:
            role = 'assistant' if message.get('author_id') == 'gm' else 'user'
            content = f"[{message.get('author_name', 'Player')}]: {message.get('content', '')}"
            messages.append({"role": role, "content": content})

        messages.append({
            "role": "user",
            "content": "Based on the memories and recent chat history, provide a summary and ask what we do next."
        })

        messages = self._coalesce_same_role(messages)
        raw_response = await self.provider.generate_completion_non_stream(messages)
        return self._parse_llm_output(raw_response)
