# server/audio_manager.py
from __future__ import annotations

import re
import uuid
import yaml
import importlib
from pathlib import Path
from typing import Dict, Any, List, Optional, TYPE_CHECKING, AsyncGenerator

import numpy as np
import soundfile as sf
from kokoro import KPipeline
import torch

from .config import settings
from .logger import logger

RVC_ENABLED = False
TTS_RVC: Any = None
try:
    _rvc_mod = importlib.import_module("tts_with_rvc")
    TTS_RVC = getattr(_rvc_mod, "TTS_RVC", None)
    RVC_ENABLED = TTS_RVC is not None
except ImportError:
    logger.warning("`tts-with-rvc` not installed. RVC functionality is disabled.")

if TYPE_CHECKING:
    from tts_with_rvc import TTS_RVC as TTS_RVC_Type
else:
    TTS_RVC_Type = Any


class AudioManager:
    def __init__(self) -> None:
        # FIX: Updated to use the new setting path from the reorganized config.
        self.output_dir = Path(settings.paths.audio_out_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.voice_cast: Dict[str, Any] = {}
        self._rvc_instances: Dict[str, TTS_RVC_Type] = {}
        self.pipeline: Optional[KPipeline] = None

        try:
            logger.info("Loading official Kokoro TTS pipeline...")
            self.pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
            logger.info("Kokoro TTS pipeline loaded successfully.")
        except Exception as e:
            logger.critical(f"Could not load Kokoro TTS pipeline: {e}", exc_info=True)
            raise

        if settings.audio.enable_dynamic_casting:
            logger.info("Dynamic Voice Casting is ENABLED.")
            self._load_voice_casting_sheet()
            if RVC_ENABLED:
                self._initialize_rvc_instances()
        else:
            logger.info("Dynamic Voice Casting is DISABLED.")

    def _load_voice_casting_sheet(self) -> None:
        try:
            # FIX: Updated to use the new setting path from the reorganized config.
            path = Path(settings.paths.voices_file)
            if not path.exists():
                logger.warning(f"Voice casting file not found at '{path}'. No custom voices will be used.")
                return
            with open(path, "r", encoding="utf-8") as f:
                self.voice_cast = yaml.safe_load(f) or {}
                logger.info(f"Successfully loaded voice casting sheet from '{path}'.")
        except Exception:
            logger.error("Failed to load or parse voices.yml.", exc_info=True)

    def _initialize_rvc_instances(self) -> None:
        # (This method is for future RVC implementation)
        pass

    @staticmethod
    def _sanitize_for_tts(text: str) -> str:
        text = re.sub(r"[\*_]", "", text)
        text = re.sub(r"\[.*?\]", "", text)
        text = re.sub(r"\(.*?\)", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _normalize_audio_chunk(self, audio_chunk: Any) -> Optional[np.ndarray]:
        if audio_chunk is None: return None
        if hasattr(audio_chunk, "detach"):
            try:
                audio_chunk = audio_chunk.detach().cpu().numpy()
            except Exception: return None
        if isinstance(audio_chunk, np.ndarray):
            return audio_chunk.flatten().astype(np.float32, copy=False)
        return None

    async def _synthesize_kokoro_stream(self, text: str, voice_name: str) -> AsyncGenerator[bytes, None]:
        if not self.pipeline:
            logger.error("Kokoro pipeline not initialized. Cannot synthesize.")
            return
        sanitized_text = self._sanitize_for_tts(text)
        if not sanitized_text: return
        generator = self.pipeline(sanitized_text, voice=voice_name, speed=1)
        for _, _, chunk in generator:
            normalized_chunk = self._normalize_audio_chunk(chunk)
            if normalized_chunk is not None and normalized_chunk.size > 0:
                yield normalized_chunk.tobytes()

    async def _synthesize_rvc_non_stream(self, text: str, character_name: str) -> np.ndarray:
        char_key = character_name.lower()
        narrator_voice = self.voice_cast.get("defaults", {}).get("narrator", settings.audio.default_voice)

        if char_key not in self._rvc_instances:
            logger.warning(f"No RVC instance found for '{character_name}'. Falling back to narrator voice.")
            audio_chunks = []
            async for chunk in self._synthesize_kokoro_stream(text, narrator_voice):
                audio_chunks.append(chunk)
            audio_bytes = b"".join(audio_chunks)
            return np.frombuffer(audio_bytes, dtype=np.float32) if audio_bytes else np.array([], dtype=np.float32)

        rvc_instance = self._rvc_instances[char_key]
        voice_info = self.voice_cast.get("characters", {}).get(character_name, {}) or {}
        base_voice = voice_info.get("base_voice", narrator_voice)
        rvc_instance.set_voice(base_voice)

        try:
            converted_audio_path_str = rvc_instance(text=text)
            if converted_audio_path_str and Path(converted_audio_path_str).exists():
                converted_audio, _ = sf.read(converted_audio_path_str)
                Path(converted_audio_path_str).unlink(missing_ok=True)
                normalized_audio = self._normalize_audio_chunk(converted_audio)
                return normalized_audio if normalized_audio is not None else np.array([], dtype=np.float32)
            else:
                logger.error(f"RVC conversion failed for '{character_name}'. Falling back to base voice.")
                audio_chunks = []
                async for chunk in self._synthesize_kokoro_stream(text, base_voice):
                    audio_chunks.append(chunk)
                audio_bytes = b"".join(audio_chunks)
                return np.frombuffer(audio_bytes, dtype=np.float32) if audio_bytes else np.array([], dtype=np.float32)
        except Exception:
            logger.error(f"An exception occurred during RVC synthesis for '{character_name}'.", exc_info=True)
            audio_chunks = []
            async for chunk in self._synthesize_kokoro_stream(text, base_voice):
                audio_chunks.append(chunk)
            audio_bytes = b"".join(audio_chunks)
            return np.frombuffer(audio_bytes, dtype=np.float32) if audio_bytes else np.array([], dtype=np.float32)

    async def synthesize_stream(self, text: str, voice: Optional[str] = None) -> AsyncGenerator[bytes, None]:
        if not text.strip(): return
        if not settings.audio.enable_dynamic_casting:
            chosen_voice = voice or settings.audio.default_voice
            async for chunk in self._synthesize_kokoro_stream(text, chosen_voice):
                yield chunk
        else:
            segments = re.split(r'(<v name=".*?">.*?</v>)', text, flags=re.DOTALL)
            for segment in segments:
                if not segment.strip(): continue
                dialogue_match = re.match(r'<v name="(.*?)">(.*?)</v>', segment, flags=re.DOTALL)
                if dialogue_match:
                    char_name, dialogue_text = dialogue_match.groups()
                    if char_name.lower() in self._rvc_instances and RVC_ENABLED:
                        logger.warning(f"Skipping RVC character '{char_name}' in streaming mode as it's not supported.")
                        continue
                    voice_info = self.voice_cast.get("characters", {}).get(char_name, {}) or {}
                    kokoro_voice = voice_info.get("kokoro_voice", self.voice_cast.get("defaults", {}).get("narrator", settings.audio.default_voice))
                    async for chunk in self._synthesize_kokoro_stream(dialogue_text, kokoro_voice):
                        yield chunk
                else:
                    narrator_voice = self.voice_cast.get("defaults", {}).get("narrator", settings.audio.default_voice)
                    async for chunk in self._synthesize_kokoro_stream(segment, narrator_voice):
                        yield chunk

    async def synthesize(self, text: str, voice: Optional[str] = None) -> str:
        if not text.strip():
            logger.warning("Synthesize called with empty text.")
            return ""

        full_audio_segments: List[np.ndarray] = []

        if not settings.audio.enable_dynamic_casting:
            chosen_voice = voice or settings.audio.default_voice
            audio_chunks = [chunk async for chunk in self._synthesize_kokoro_stream(text, chosen_voice)]
            audio_bytes = b"".join(audio_chunks)
            if audio_bytes:
                full_audio_segments.append(np.frombuffer(audio_bytes, dtype=np.float32))
        else:
            segments = re.split(r'(<v name=".*?">.*?</v>)', text, flags=re.DOTALL)
            for segment in segments:
                sanitized_segment = self._sanitize_for_tts(segment)
                if not sanitized_segment: continue

                dialogue_match = re.match(r'<v name="(.*?)">(.*?)</v>', segment, flags=re.DOTALL)
                if dialogue_match:
                    char_name, dialogue_text = dialogue_match.groups()
                    if char_name.lower() in self._rvc_instances and RVC_ENABLED:
                        audio_array = await self._synthesize_rvc_non_stream(dialogue_text, char_name)
                        full_audio_segments.append(audio_array)
                    else:
                        voice_info = self.voice_cast.get("characters", {}).get(char_name, {}) or {}
                        kokoro_voice = voice_info.get("kokoro_voice", self.voice_cast.get("defaults", {}).get("narrator", settings.audio.default_voice))
                        audio_chunks = [chunk async for chunk in self._synthesize_kokoro_stream(dialogue_text, kokoro_voice)]
                        audio_bytes = b"".join(audio_chunks)
                        if audio_bytes:
                            full_audio_segments.append(np.frombuffer(audio_bytes, dtype=np.float32))
                else:
                    narrator_voice = self.voice_cast.get("defaults", {}).get("narrator", settings.audio.default_voice)
                    audio_chunks = [chunk async for chunk in self._synthesize_kokoro_stream(segment, narrator_voice)]
                    audio_bytes = b"".join(audio_chunks)
                    if audio_bytes:
                        full_audio_segments.append(np.frombuffer(audio_bytes, dtype=np.float32))

        if not full_audio_segments:
            logger.warning("TTS generation produced no audio.")
            return ""

        full_audio = np.concatenate([seg for seg in full_audio_segments if seg.size > 0])
        if full_audio.size == 0:
            logger.warning("TTS concatenation resulted in empty audio.")
            return ""

        filename = f"{uuid.uuid4().hex}.wav"
        output_path = self.output_dir / filename
        sf.write(output_path, full_audio, 24000)

        url_path = f"/audio/{filename}"
        logger.info(f"Final audio synthesized successfully to '{url_path}'")
        return url_path

    def list_voices(self) -> Dict[str, List[str]]:
        try:
            defaults = self.voice_cast.get("defaults", {}) if settings.audio.enable_dynamic_casting else {}
            chars = self.voice_cast.get("characters", {}) if settings.audio.enable_dynamic_casting else {}
            kokoro_list = ["af_heart", "am_michael", "am_puck", "am_fenrir", "af_bella"]
            narrator = defaults.get("narrator")
            if narrator and narrator not in kokoro_list:
                kokoro_list.append(narrator)
            for v in chars.values():
                if isinstance(v, dict):
                    kv = v.get("kokoro_voice")
                    if kv and kv not in kokoro_list:
                        kokoro_list.append(kv)
            return {"kokoro": sorted(list(set(kokoro_list)))}
        except Exception:
            logger.error("Failed to list voices.", exc_info=True)
            return {"kokoro": ["af_heart"]}