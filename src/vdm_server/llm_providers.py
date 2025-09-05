from __future__ import annotations

import abc
import json
from typing import List, Dict, AsyncGenerator

import httpx

from .config import settings
from .logger import logger

# ===================================================================
# LLM Provider Abstraction
# ===================================================================

class LLMProvider(abc.ABC):
    """Abstract base class for all LLM providers."""

    @abc.abstractmethod
    async def generate_completion_stream(
        self, messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        # dummy yield to satisfy abstract async generator
        yield "This method needs to be implemented by a subclass"

    async def generate_completion_non_stream(self, messages: List[Dict[str, str]]) -> str:
        full_response = ""
        async for chunk in self.generate_completion_stream(messages):
            full_response += chunk
        return full_response


# ===================================================================
# STRICT LM Studio normalization for jinja template you posted
# ===================================================================

def _normalize_for_lmstudio(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Produce a sequence that *strictly* alternates starting with 'user',
    per the LM Studio jinja:

        loop_messages = messages (or messages[1:] if first is system)
        assert loop_messages[0] == user
        assert roles alternate user/assistant/user/assistant/...

    Strategy:
      - Pull *all* system text into a prefix.
      - Drop system messages from the list passed to LM Studio.
      - Rebuild a new list that *forces* exact alternation:
          expected role at index i: 'user' if i%2==0 else 'assistant'
        * If the incoming message has the expected role -> append.
        * Else -> merge its content into the previous appended message
                 (so we never create illegal alternation).
      - Ensure there is at least one 'user' at the start; if not, synthesize one.
    """
    sys_prefix = []
    non_system: List[Dict[str, str]] = []
    for m in messages:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content and isinstance(m.get("content"), list):
            # Handle multi-part content: keep only text pieces
            parts = []
            for item in m["content"]:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
            content = "\n".join(p.strip() for p in parts if p.strip())
        if role == "system":
            if content:
                sys_prefix.append(content)
        elif role in ("user", "assistant"):
            non_system.append({"role": role, "content": content})

    # If nothing left, create a single user with any system text
    system_blob = "\n\n".join(sys_prefix).strip()
    if not non_system:
        return [{"role": "user", "content": system_blob}]

    # Build strictly alternating sequence
    out: List[Dict[str, str]] = []

    # First turn MUST be user. Seed it.
    first_user_content = ""
    if system_blob:
        first_user_content = system_blob

    # Try to use the first incoming user content as well
    # (if the first incoming message is user, fold system into it)
    i = 0
    if non_system[0]["role"] == "user":
        first_user_content = (first_user_content + ("\n\n" if first_user_content else "") + non_system[0]["content"]).strip()
        i = 1  # we've consumed the first incoming message

    # If we still have no first user content, synthesize empty
    out.append({"role": "user", "content": first_user_content})

    # Walk remaining incoming messages and force alternation
    expected = "assistant"  # since we just pushed a user
    while i < len(non_system):
        m = non_system[i]
        if m["role"] == expected:
            # append as its own turn
            out.append({"role": expected, "content": m["content"]})
            expected = "user" if expected == "assistant" else "assistant"
        else:
            # role mismatch: fold into the previous turn's content
            # (safe because we maintain strict alternation in 'out')
            out[-1]["content"] = (out[-1]["content"] + ("\n\n" if out[-1]["content"] else "") + m["content"]).strip()
            # 'expected' unchanged; we did not advance alternation
        i += 1

    # Optional: trim leading/trailing empties for neatness (not required)
    if out and not out[0]["content"]:
        out[0]["content"] = ""  # keep empty; template allows empty user
    if out and not out[-1]["content"]:
        pass

    # Debug log to inspect roles if needed
    try:
        role_seq = [m["role"] for m in out]
        logger.debug(f"LMStudio normalized roles: {role_seq}")
    except Exception:
        pass

    return out


# ===================================================================
# Providers
# ===================================================================

class OpenRouterProvider(LLMProvider):
    def __init__(self):
        self.api_key = settings.llm_providers.openrouter.api_key
        if not self.api_key or "sk-or-" not in self.api_key:
            raise ValueError("OpenRouter API key is missing or invalid in your .env file")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = settings.llm.story_model

    async def generate_completion_stream(
        self, messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            try:
                async with client.stream("POST", self.api_url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[len("data: "):]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                content = data.get("choices", [{}])[0].get("delta", {}).get("content")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
            except httpx.HTTPStatusError as e:
                body = e.response.text
                logger.error(f"HTTP error from OpenRouter: {e.response.status_code} - {body}")
                yield "Error: Connection to OpenRouter failed."
            except Exception:
                logger.error("Could not get completion stream from OpenRouter.", exc_info=True)
                yield "Error: A problem occurred while contacting OpenRouter."


class OllamaProvider(LLMProvider):
    def __init__(self):
        self.base_url = settings.llm_providers.ollama.base_url
        self.api_url = f"{self.base_url.rstrip('/')}/api/chat"
        self.model = settings.llm.story_model

    async def generate_completion_stream(
        self, messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            try:
                async with client.stream("POST", self.api_url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                content = data.get("message", {}).get("content")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
            except httpx.HTTPStatusError as e:
                body = e.response.text
                logger.error(f"HTTP error from Ollama: {e.response.status_code} - {body}")
                yield "Error: Could not connect to the local Ollama instance."
            except Exception:
                logger.error("Could not get completion stream from Ollama.", exc_info=True)
                yield "Error: A problem occurred while contacting Ollama."


class LMStudioProvider(LLMProvider):
    def __init__(self):
        self.base_url = settings.llm_providers.lmstudio.base_url
        self.api_url = f"{self.base_url.rstrip('/')}/chat/completions"
        self.model = settings.llm.story_model

    async def generate_completion_stream(
        self, messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        # Strict alternation required by your jinja template
        safe_messages = _normalize_for_lmstudio(messages)

        payload = {
            "model": self.model,
            "messages": safe_messages,
            "stream": True,
        }
        # Optional: log role sequence we actually send
        try:
            logger.debug(f"Sending to LM Studio roles: {[m['role'] for m in safe_messages]}")
        except Exception:
            pass

        async with httpx.AsyncClient(timeout=120) as client:
            try:
                async with client.stream("POST", self.api_url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[len("data: "):]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                content = data.get("choices", [{}])[0].get("delta", {}).get("content")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
            except httpx.HTTPStatusError as e:
                body = e.response.text
                logger.error(f"HTTP error from LM Studio: {e.response.status_code} - {body}")
                yield "Error: Could not get a response from LM Studio."
            except Exception:
                logger.error("Could not get completion stream from LM Studio.", exc_info=True)
                yield "Error: A problem occurred while contacting LM Studio."


def make_llm_provider() -> LLMProvider:
    backend = settings.llm.backend.lower()
    if backend == "openrouter":
        logger.info("Using OpenRouter LLM provider.")
        return OpenRouterProvider()
    elif backend == "ollama":
        logger.info("Using Ollama LLM provider.")
        return OllamaProvider()
    elif backend == "lmstudio":
        logger.info("Using LM Studio LLM provider.")
        return LMStudioProvider()
    else:
        raise ValueError(f"Unknown LLM backend specified in settings.yml: {backend}")
