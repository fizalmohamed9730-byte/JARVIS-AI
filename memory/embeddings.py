"""
Embedding Management for JARVIS Memory System.

Provides text embedding generation with online (OpenAI) and offline
(sentence-transformers) backends, plus cosine similarity utilities.
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """
    Manages text embeddings for semantic search.

    Supports OpenAI embeddings (online) and sentence-transformers (offline)
    with automatic fallback between backends.
    """

    def __init__(self):
        self._online_model = None
        self._offline_model = None
        self._online_client = None
        self._active_backend: str = "offline"
        self._model_name: str = "all-MiniLM-L6-v2"
        self._embedding_dim: int = 384
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Return True if at least one backend is ready."""
        return self._initialized

    @property
    def embedding_dim(self) -> int:
        """Return the dimension of generated embeddings."""
        return self._embedding_dim

    @property
    def active_backend(self) -> str:
        """Return the name of the active embedding backend."""
        return self._active_backend

    async def initialize(
        self,
        backend: str = "auto",
        model_name: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        openai_model: str = "text-embedding-3-small",
    ) -> None:
        """
        Initialize the embedding manager.

        Args:
            backend: "online", "offline", or "auto" (tries online, falls back to offline).
            model_name: Sentence-transformers model name for offline mode.
            openai_api_key: OpenAI API key for online mode.
            openai_model: OpenAI embedding model name.

        Raises:
            RuntimeError: If no backend can be initialized.
        """
        if backend in ("online", "auto"):
            try:
                await self._init_online(openai_api_key, openai_model)
                self._active_backend = "online"
                self._initialized = True
                logger.info("Online embedding backend initialized (%s)", openai_model)
                if backend == "online":
                    return
            except Exception as e:
                logger.warning("Online embedding init failed: %s", e)
                if backend == "online":
                    raise

        if backend in ("offline", "auto"):
            try:
                offline_name = model_name or self._model_name
                await self._init_offline(offline_name)
                self._active_backend = "offline"
                self._initialized = True
                logger.info("Offline embedding backend initialized (%s)", offline_name)
                return
            except Exception as e:
                logger.warning("Offline embedding init failed: %s", e)
                if backend == "offline":
                    raise

        if not self._initialized:
            raise RuntimeError("No embedding backend could be initialized")

    async def _init_online(self, api_key: Optional[str], model: str) -> None:
        """Initialize the OpenAI embedding client."""
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package required for online embeddings")

        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError("OpenAI API key required for online embeddings")

        self._online_client = AsyncOpenAI(api_key=key)
        self._online_model = model

        dims_resp = await self._online_client.embeddings.create(
            model=model,
            input=["test"],
        )
        self._embedding_dim = len(dims_resp.data[0].embedding)

    async def _init_offline(self, model_name: str) -> None:
        """Initialize the sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers required for offline embeddings. "
                "Install with: pip install sentence-transformers"
            )

        loop = asyncio.get_event_loop()
        model = await loop.run_in_executor(
            None, SentenceTransformer, model_name
        )
        self._offline_model = model
        self._model_name = model_name
        self._embedding_dim = model.get_sentence_embedding_dimension()

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for a text string.

        Args:
            text: Input text to embed.

        Returns:
            List of floats representing the embedding vector.

        Raises:
            RuntimeError: If the manager is not initialized.
        """
        if not self._initialized:
            raise RuntimeError("EmbeddingManager not initialized")

        if self._active_backend == "online":
            return await self._generate_online(text)
        return await self._generate_offline(text)

    async def _generate_online(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        response = await self._online_client.embeddings.create(
            model=self._online_model,
            input=text,
        )
        return response.data[0].embedding

    async def _generate_offline(self, text: str) -> List[float]:
        """Generate embedding using sentence-transformers."""
        loop = asyncio.get_event_loop()

        def _encode():
            embedding = self._offline_model.encode(text, normalize_embeddings=True)
            return embedding.tolist()

        return await loop.run_in_executor(None, _encode)

    async def batch_embed(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of text strings to embed.
            batch_size: Number of texts to process per batch (offline only).

        Returns:
            List of embedding vectors, one per input text.
        """
        if not self._initialized:
            raise RuntimeError("EmbeddingManager not initialized")
        if not texts:
            return []

        if self._active_backend == "online":
            return await self._batch_embed_online(texts)
        return await self._batch_embed_offline(texts, batch_size)

    async def _batch_embed_online(self, texts: List[str]) -> List[List[float]]:
        """Batch embed using OpenAI API."""
        results = []
        batch_size = 2048
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await self._online_client.embeddings.create(
                model=self._online_model,
                input=batch,
            )
            sorted_data = sorted(response.data, key=lambda x: x.index)
            results.extend([item.embedding for item in sorted_data])
        return results

    async def _batch_embed_offline(self, texts: List[str], batch_size: int) -> List[List[float]]:
        """Batch embed using sentence-transformers."""
        loop = asyncio.get_event_loop()

        def _encode():
            embeddings = self._offline_model.encode(
                texts,
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return [emb.tolist() for emb in embeddings]

        return await loop.run_in_executor(None, _encode)

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            a: First embedding vector.
            b: Second embedding vector.

        Returns:
            Similarity score between -1.0 and 1.0.
        """
        a_arr = np.asarray(a, dtype=np.float64)
        b_arr = np.asarray(b, dtype=np.float64)

        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))

    @staticmethod
    def batch_cosine_similarity(
        query: List[float],
        embeddings: List[List[float]],
    ) -> List[float]:
        """
        Calculate cosine similarity between a query and multiple embeddings.

        Args:
            query: Query embedding vector.
            embeddings: List of candidate embedding vectors.

        Returns:
            List of similarity scores.
        """
        if not embeddings:
            return []

        query_arr = np.asarray(query, dtype=np.float64)
        emb_matrix = np.asarray(embeddings, dtype=np.float64)

        query_norm = np.linalg.norm(query_arr)
        if query_norm == 0:
            return [0.0] * len(embeddings)

        emb_norms = np.linalg.norm(emb_matrix, axis=1)
        emb_norms[emb_norms == 0] = 1.0

        similarities = emb_matrix @ query_arr / (emb_norms * query_norm)
        return similarities.tolist()

    def switch_backend(self, backend: str) -> None:
        """
        Switch between online and offline backends.

        Args:
            backend: "online" or "offline".

        Raises:
            RuntimeError: If the requested backend is not initialized.
        """
        if backend == "online" and self._online_client is None:
            raise RuntimeError("Online backend not initialized")
        if backend == "offline" and self._offline_model is None:
            raise RuntimeError("Offline backend not initialized")

        self._active_backend = backend
        logger.info("Embedding backend switched to '%s'", backend)

    def cleanup(self) -> None:
        """Release resources."""
        self._offline_model = None
        self._online_client = None
        self._initialized = False
        logger.info("Embedding manager cleaned up")
