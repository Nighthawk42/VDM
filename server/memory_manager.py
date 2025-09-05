# server/memory_manager.py
from __future__ import annotations

from pathlib import Path
from typing import List, Iterable, Dict, Any, Optional, TypedDict, cast
import re
import time
import uuid
import numpy as np

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from .config import settings
from .logger import logger

# ---------- Simple sentence splitting & chunking ----------

def _sentence_split(text: str) -> List[str]:
    """Lightweight sentence splitter; avoids heavy deps."""
    t = re.sub(r"\s+", " ", text).strip()
    if not t:
        return []
    parts = re.split(r"(?<=[.!?])\s+", t)
    return [p.strip() for p in parts if p.strip()]


def _chunk_sentences(
    sentences: List[str],
    max_chars: int = 700,
    overlap: int = 1,
) -> List[str]:
    """Pack sentences into ~max_chars chunks with small overlap for recall."""
    chunks: List[str] = []
    buf: List[str] = []
    cur = 0
    for s in sentences:
        if cur + len(s) + (1 if buf else 0) > max_chars and buf:
            chunks.append(" ".join(buf))
            buf = buf[-overlap:] if overlap > 0 else []
            cur = sum(len(x) for x in buf) + (len(buf) - 1 if buf else 0)
        if cur > 0:
            cur += 1
        buf.append(s)
        cur += len(s)
    if buf:
        chunks.append(" ".join(buf))
    return chunks


# ---------- Embedding wrapper ----------

class _STEmbedder:
    """Sentence-Transformers wrapper that returns numpy arrays with the right dtype."""
    def __init__(self, model_name: str) -> None:
        self.model = SentenceTransformer(model_name, device="cpu")
        logger.info(f"SentenceTransformer loaded: {model_name}")

    def embed(self, texts: Iterable[str]) -> np.ndarray:
        arr = self.model.encode(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        if not isinstance(arr, np.ndarray):
            arr = np.asarray(arr)
        if arr.dtype != np.float32:
            arr = arr.astype(np.float32, copy=False)
        return arr


# ---------- Metadata shape (all primitives) ----------

Primitive = str | int | float | bool | None

class MemoryMeta(TypedDict, total=False):
    room_id: str
    ts: int
    len: int


# ---------- Memory manager ----------

class MemoryManager:
    def __init__(self):
        # FIX: Updated to use the new setting path from the reorganized config.
        self.memory_dir = Path(settings.paths.memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        try:
            chroma_settings = ChromaSettings(anonymized_telemetry=False)
            self.chroma = chromadb.PersistentClient(
                path=str(self.memory_dir / "chroma_db"),
                settings=chroma_settings,
            )
            logger.info("ChromaDB PersistentClient initialized (telemetry OFF).")
            # FIX: Now uses the embedding model specified in the settings file.
            self.embedder = _STEmbedder(settings.memory.embedding_model)
        except Exception:
            logger.critical("Failed to initialize MemoryManager.", exc_info=True)
            raise

    def _collection_name(self, room_id: str) -> str:
        return f"vdm_{room_id}"

    def _get_collection(self, room_id: str):
        return self.chroma.get_or_create_collection(
            name=self._collection_name(room_id),
            metadata={"hnsw:space": "cosine"},
        )

    def add_memory(self, room_id: str, text: str) -> None:
        if not text or not text.strip():
            return
        try:
            sentences = _sentence_split(text)
            if not sentences: return
            chunks: List[str] = _chunk_sentences(sentences, max_chars=700, overlap=1)
            if not chunks: return

            embeds_np: np.ndarray = self.embedder.embed(chunks)
            col = self._get_collection(room_id)

            ts = int(time.time())
            ids: List[str] = [uuid.uuid4().hex for _ in chunks]
            metadatas: List[Dict[str, Primitive]] = [
                {"room_id": room_id, "ts": ts, "len": len(c)} for c in chunks
            ]
            col.add(
                ids=ids,
                documents=chunks,
                embeddings=cast(Any, embeds_np),
                metadatas=cast(Any, metadatas),
            )
            logger.info(f"Added {len(chunks)} memory chunk(s) to room '{room_id}'.")
        except Exception:
            logger.error(f"Failed to add memory to room '{room_id}'.", exc_info=True)

    def search_memory(self, room_id: str, query_text: str, k: int = 3) -> List[str]:
        if not query_text or not query_text.strip():
            return []
        try:
            col = self._get_collection(room_id)
            if col.count() == 0:
                return []

            q_np: np.ndarray = self.embedder.embed([query_text])
            result = col.query(
                query_embeddings=cast(Any, q_np),
                n_results=max(1, k),
            )
            docs = (result.get("documents") or [[]])[0]
            return [d for d in docs if d]
        except Exception:
            logger.error(f"Failed to search memory for room '{room_id}'.", exc_info=True)
            return []