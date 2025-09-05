# server/memory_manager.py
"""
Manages the long-term memory of the AI Game Master using a vector database.
"""
from __future__ import annotations

import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, cast, TYPE_CHECKING

import chromadb
import numpy as np
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from .config import settings
from .logger import logger

# This block is for static analysis only (for Pylance).
if TYPE_CHECKING:
    from chonkie import SemanticChunker
    from chonkie.embeddings import SentenceTransformerEmbeddings
    from chonkie.types import Chunk


class _STEmbedder:
    """A simple fallback embedder using sentence-transformers."""
    def __init__(self, model_name: str) -> None:
        self.model = SentenceTransformer(model_name, device="cpu")
        logger.info(f"SentenceTransformer loaded: {model_name}")

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        arr = self.model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        if not isinstance(arr, np.ndarray):
            arr = np.asarray(arr)
        if arr.dtype != np.float32:
            arr = arr.astype(np.float32, copy=False)
        return arr

# --- (Metadata types are unchanged) ---
Primitive = str | int | float | bool | None
class MemoryMeta(TypedDict, total=False):
    room_id: str
    ts: int
    len: int


class MemoryManager:
    """Manages the vector database for the AI's long-term memory."""
    def __init__(self):
        """Initializes the ChromaDB client and the selected chunking/embedding strategy."""
        self.memory_dir = Path(settings.paths.memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.chunker: Optional["SemanticChunker"] = None
        self.embedder: Any = None

        try:
            chroma_settings = ChromaSettings(anonymized_telemetry=False)
            self.chroma = chromadb.PersistentClient(path=str(self.memory_dir / "chroma_db"), settings=chroma_settings)
            logger.info("ChromaDB PersistentClient initialized (telemetry OFF).")

            if settings.memory.chunker == "chonkie":
                try:
                    from chonkie import SemanticChunker
                    from chonkie.embeddings import SentenceTransformerEmbeddings
                except ImportError:
                    raise ImportError("Chonkie is configured but not installed correctly. Please run 'uv pip install \"chonkie[st]\"'.")
                
                logger.info("Initializing Chonkie with SemanticChunker...")
                # FIXED: Changed keyword from 'model_name' to 'model'
                embedding_handler = SentenceTransformerEmbeddings(
                    model=settings.memory.embedding_model, 
                    device="cpu"
                )
                self.chunker = SemanticChunker(embedding_model=embedding_handler)
                self.embedder = embedding_handler
                logger.info("Using 'chonkie' for text chunking.")
            else:
                self.embedder = _STEmbedder(settings.memory.embedding_model)
                logger.info("Using 'simple' fallback for text chunking.")

        except Exception:
            logger.critical("Failed to initialize MemoryManager.", exc_info=True)
            raise

    @staticmethod
    def _simple_chunker(text: str) -> List[str]:
        # ... (implementation is unchanged)
        t = re.sub(r"\s+", " ", text).strip()
        if not t: return []
        sentences = [p.strip() for p in re.split(r"(?<=[.!?])\s+", t) if p.strip()]
        if not sentences: return []
        chunks: List[str] = []; buf: List[str] = []; cur = 0
        for s in sentences:
            if cur + len(s) + (1 if buf else 0) > 700 and buf:
                chunks.append(" ".join(buf)); buf = buf[-1:]; cur = sum(len(x) for x in buf) + (len(buf) - 1 if buf else 0)
            if cur > 0: cur += 1
            buf.append(s); cur += len(s)
        if buf: chunks.append(" ".join(buf))
        return chunks

    def _get_collection(self, room_id: str) -> chromadb.Collection:
        # ... (implementation is unchanged)
        return self.chroma.get_or_create_collection(name=f"vdm_{room_id}", metadata={"hnsw:space": "cosine"})

    def add_memory(self, room_id: str, text: str) -> None:
        """Adds a piece of text to the long-term memory for a room."""
        if not text or not text.strip(): return
        try:
            if settings.memory.chunker == "chonkie" and self.chunker:
                chonkie_chunks = self.chunker(text)
                chunks = [c.text for c in chonkie_chunks if c.text.strip()] # type: ignore (This *might* break things)
            else:
                chunks = self._simple_chunker(text)

            if not chunks: return

            if "embeddinggemma" in settings.memory.embedding_model:
                formatted_chunks_for_embedding = [f"text: {c}" for c in chunks]
            else:
                formatted_chunks_for_embedding = chunks

            embeds_np: np.ndarray = self.embedder.embed_batch(formatted_chunks_for_embedding)
            
            col = self._get_collection(room_id)
            ts = int(time.time())
            ids: List[str] = [uuid.uuid4().hex for _ in chunks]
            metadatas: List[Dict[str, Primitive]] = [{"room_id": room_id, "ts": ts, "len": len(c)} for c in chunks]
            
            col.add(ids=ids, documents=chunks, embeddings=cast(Any, embeds_np), metadatas=cast(Any, metadatas))
            logger.info(f"Added {len(chunks)} memory chunk(s) to room '{room_id}' using '{settings.memory.chunker}' chunker.")
        except Exception:
            logger.error(f"Failed to add memory to room '{room_id}'.", exc_info=True)

    def search_memory(self, room_id: str, query_text: str, k: int = 3) -> List[str]:
        # ... (implementation is unchanged)
        if not query_text or not query_text.strip(): return []
        try:
            col = self._get_collection(room_id)
            if col.count() == 0: return []

            if "embeddinggemma" in settings.memory.embedding_model:
                formatted_query = f"task: search result | query: {query_text}"
            else:
                formatted_query = query_text
            
            q_np: np.ndarray = self.embedder.embed_batch([formatted_query])
            
            result = col.query(query_embeddings=cast(Any, q_np), n_results=max(1, k))
            docs = (result.get("documents") or [[]])[0]
            return [d for d in docs if d]
        except Exception:
            logger.error(f"Failed to search memory for room '{room_id}'.", exc_info=True)
            return []