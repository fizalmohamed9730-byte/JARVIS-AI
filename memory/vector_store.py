"""
Vector Store Abstraction for JARVIS Memory System.

Provides a unified interface over ChromaDB (persistent) and FAISS (fast in-memory)
with hybrid search capabilities.
"""

import asyncio
import json
import logging
import os
import pickle
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class VectorDocument:
    """Represents a document stored in the vector store."""

    def __init__(
        self,
        doc_id: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.doc_id = doc_id
        self.text = text
        self.embedding = embedding
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.doc_id,
            "text": self.text,
            "embedding": self.embedding,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VectorDocument":
        """Create from dictionary."""
        return cls(
            doc_id=data["id"],
            text=data["text"],
            embedding=data["embedding"],
            metadata=data.get("metadata", {}),
        )


class SearchResult:
    """Represents a single search result."""

    def __init__(
        self,
        document: VectorDocument,
        score: float,
        backend: str,
    ):
        self.document = document
        self.score = score
        self.backend = backend

    def __repr__(self) -> str:
        return (
            f"SearchResult(id={self.document.doc_id!r}, "
            f"score={self.score:.4f}, backend={self.backend!r})"
        )


class ChromaDBBackend:
    """Persistent vector storage using ChromaDB."""

    def __init__(self, collection_name: str = "jarvis_memory", persist_dir: Optional[str] = None):
        self._collection_name = collection_name
        self._persist_dir = persist_dir or str(Path.home() / ".jarvis" / "data" / "chromadb")
        self._client = None
        self._collection = None

    async def initialize(self) -> None:
        """Initialize ChromaDB client and collection."""
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            raise ImportError(
                "chromadb is required. Install with: pip install chromadb"
            )

        loop = asyncio.get_event_loop()

        def _init():
            os.makedirs(self._persist_dir, exist_ok=True)
            client = chromadb.PersistentClient(path=self._persist_dir)
            collection = client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            return client, collection

        self._client, self._collection = await loop.run_in_executor(None, _init)
        logger.info(
            "ChromaDB backend initialized (collection=%s, dir=%s)",
            self._collection_name,
            self._persist_dir,
        )

    async def add_document(
        self,
        doc_id: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a document to ChromaDB."""
        meta = metadata or {}
        # ChromaDB metadata values must be str, int, float, or bool
        safe_meta = {}
        for k, v in meta.items():
            if isinstance(v, (str, int, float, bool)):
                safe_meta[k] = v
            else:
                safe_meta[k] = str(v)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._collection.upsert(
                ids=[doc_id],
                documents=[text],
                embeddings=[embedding],
                metadatas=[safe_meta] if safe_meta else None,
            ),
        )

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search ChromaDB for similar documents."""
        where = None
        if filters:
            where = {}
            for k, v in filters.items():
                if isinstance(v, (str, int, float, bool)):
                    where[k] = v
                else:
                    where[k] = str(v)

        loop = asyncio.get_event_loop()

        def _search():
            kwargs = {
                "query_embeddings": [query_embedding],
                "n_results": min(top_k, self._collection.count() or 1),
            }
            if where:
                kwargs["where"] = where
            return self._collection.query(**kwargs)

        results = await loop.run_in_executor(None, _search)

        search_results = []
        if results and results["ids"] and results["ids"][0]:
            ids = results["ids"][0]
            documents = results["documents"][0] if results["documents"] else [""] * len(ids)
            distances = results["distances"][0] if results["distances"] else [0.0] * len(ids)
            metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(ids)

            for i, doc_id in enumerate(ids):
                score = 1.0 - distances[i] if distances[i] <= 2.0 else 0.0
                doc = VectorDocument(
                    doc_id=doc_id,
                    text=documents[i] if i < len(documents) else "",
                    embedding=[],
                    metadata=metadatas[i] if i < len(metadatas) else {},
                )
                search_results.append(SearchResult(document=doc, score=score, backend="chromadb"))

        return search_results

    async def delete(self, doc_id: str) -> bool:
        """Delete a document by ID."""
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None, lambda: self._collection.delete(ids=[doc_id])
            )
            return True
        except Exception as e:
            logger.error("ChromaDB delete failed: %s", e)
            return False

    async def update(
        self,
        doc_id: str,
        text: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update a document's text, embedding, or metadata."""
        try:
            update_kwargs = {"ids": [doc_id]}
            if text is not None:
                update_kwargs["documents"] = [text]
            if embedding is not None:
                update_kwargs["embeddings"] = [embedding]
            if metadata is not None:
                safe_meta = {k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool))}
                update_kwargs["metadatas"] = [safe_meta]

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: self._collection.update(**update_kwargs)
            )
            return True
        except Exception as e:
            logger.error("ChromaDB update failed: %s", e)
            return False

    async def count(self) -> int:
        """Return the number of documents."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._collection.count)

    def cleanup(self) -> None:
        """Release resources."""
        self._client = None
        self._collection = None


class FAISSBackend:
    """Fast in-memory vector search using FAISS."""

    def __init__(self, dimension: int = 384):
        self._dimension = dimension
        self._index = None
        self._documents: Dict[str, VectorDocument] = {}
        self._id_map: Dict[int, str] = {}
        self._reverse_id_map: Dict[str, int] = {}
        self._next_idx: int = 0
        self._lock = threading.Lock()

    async def initialize(self, dimension: int = 384) -> None:
        """Initialize the FAISS index."""
        try:
            import faiss
        except ImportError:
            raise ImportError(
                "faiss-cpu is required. Install with: pip install faiss-cpu"
            )

        self._dimension = dimension
        loop = asyncio.get_event_loop()

        def _init():
            index = faiss.IndexFlatIP(dimension)
            return index

        self._index = await loop.run_in_executor(None, _init)
        logger.info("FAISS backend initialized (dimension=%d)", dimension)

    async def add_document(
        self,
        doc_id: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a document to the FAISS index."""
        try:
            import faiss
        except ImportError:
            raise ImportError("faiss-cpu required")

        with self._lock:
            if doc_id in self._reverse_id_map:
                old_idx = self._reverse_id_map[doc_id]
                new_vec = np.array([embedding], dtype=np.float32)
                faiss.normalize_L2(new_vec)
                self._index.remove_ids(np.array([old_idx]))
                new_faiss_idx = self._index.add(new_vec)
                self._id_map[new_faiss_idx] = doc_id
                self._reverse_id_map[doc_id] = new_faiss_idx
                self._documents[doc_id] = VectorDocument(doc_id, text, embedding, metadata)
            else:
                new_vec = np.array([embedding], dtype=np.float32)
                faiss.normalize_L2(new_vec)
                faiss_idx = self._index.add(new_vec)
                self._id_map[faiss_idx] = doc_id
                self._reverse_id_map[doc_id] = faiss_idx
                self._documents[doc_id] = VectorDocument(doc_id, text, embedding, metadata)

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search FAISS for similar documents."""
        try:
            import faiss
        except ImportError:
            raise ImportError("faiss-cpu required")

        if self._index.ntotal == 0:
            return []

        query_vec = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_vec)

        k = min(top_k, self._index.ntotal)
        loop = asyncio.get_event_loop()

        def _search():
            distances, indices = self._index.search(query_vec, k)
            return distances[0], indices[0]

        distances, indices = await loop.run_in_executor(None, _search)

        results = []
        for dist, idx in zip(distances, indices):
            if idx == -1:
                continue
            doc_id = self._id_map.get(int(idx))
            if doc_id is None:
                continue
            doc = self._documents.get(doc_id)
            if doc is None:
                continue

            if filters:
                match = all(doc.metadata.get(k) == v for k, v in filters.items())
                if not match:
                    continue

            score = float(dist)
            results.append(SearchResult(document=doc, score=score, backend="faiss"))

        return results

    async def delete(self, doc_id: str) -> bool:
        """Delete a document from the index."""
        try:
            import faiss
        except ImportError:
            raise ImportError("faiss-cpu required")

        with self._lock:
            if doc_id not in self._reverse_id_map:
                return False
            idx = self._reverse_id_map[doc_id]
            self._index.remove_ids(np.array([idx]))
            del self._documents[doc_id]
            del self._id_map[idx]
            del self._reverse_id_map[doc_id]
            return True

    async def update(
        self,
        doc_id: str,
        text: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update a document's content or embedding."""
        if doc_id not in self._documents:
            return False

        doc = self._documents[doc_id]
        if text is not None:
            doc.text = text
        if metadata is not None:
            doc.metadata.update(metadata)
        if embedding is not None:
            doc.embedding = embedding
            await self.add_document(doc_id, doc.text, doc.embedding, doc.metadata)
        return True

    async def count(self) -> int:
        """Return the number of indexed documents."""
        return self._index.ntotal if self._index else 0

    async def save(self, path: str) -> None:
        """Save the FAISS index and document map to disk."""
        try:
            import faiss
        except ImportError:
            raise ImportError("faiss-cpu required")

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        loop = asyncio.get_event_loop()

        def _save():
            faiss.write_index(self._index, path + ".faiss")
            with open(path + ".meta", "wb") as f:
                pickle.dump(
                    {
                        "id_map": self._id_map,
                        "reverse_id_map": self._reverse_id_map,
                        "next_idx": self._next_idx,
                        "documents": {k: v.to_dict() for k, v in self._documents.items()},
                        "dimension": self._dimension,
                    },
                    f,
                )

        await loop.run_in_executor(None, _save)
        logger.info("FAISS index saved to %s", path)

    async def load(self, path: str) -> None:
        """Load a FAISS index and document map from disk."""
        try:
            import faiss
        except ImportError:
            raise ImportError("faiss-cpu required")

        loop = asyncio.get_event_loop()

        def _load():
            index = faiss.read_index(path + ".faiss")
            with open(path + ".meta", "rb") as f:
                meta = pickle.load(f)
            return index, meta

        self._index, meta = await loop.run_in_executor(None, _load)
        self._id_map = meta["id_map"]
        self._reverse_id_map = meta["reverse_id_map"]
        self._next_idx = meta["next_idx"]
        self._dimension = meta["dimension"]
        self._documents = {
            k: VectorDocument.from_dict(v) for k, v in meta["documents"].items()
        }
        logger.info("FAISS index loaded from %s (%d documents)", path, self._index.ntotal)

    def cleanup(self) -> None:
        """Release resources."""
        self._index = None
        self._documents.clear()
        self._id_map.clear()
        self._reverse_id_map.clear()


class VectorStoreManager:
    """
    Unified vector store manager with ChromaDB and FAISS backends.

    ChromaDB provides persistent storage with metadata filtering.
    FAISS provides fast in-memory search with index serialization.
    Hybrid mode uses both for redundancy and performance.
    """

    def __init__(self):
        self._chroma: Optional[ChromaDBBackend] = None
        self._faiss: Optional[FAISSBackend] = None
        self._primary: str = "chromadb"
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Return True if at least one backend is ready."""
        return self._initialized

    async def initialize(
        self,
        primary: str = "chromadb",
        embedding_dim: int = 384,
        chroma_collection: str = "jarvis_memory",
        chroma_persist_dir: Optional[str] = None,
        enable_faiss: bool = True,
    ) -> None:
        """
        Initialize vector store backends.

        Args:
            primary: Primary backend ("chromadb", "faiss", or "hybrid").
            embedding_dim: Dimension of embedding vectors.
            chroma_collection: ChromaDB collection name.
            chroma_persist_dir: ChromaDB persistence directory.
            enable_faiss: Whether to also initialize FAISS.
        """
        self._primary = primary

        if primary in ("chromadb", "hybrid"):
            self._chroma = ChromaDBBackend(chroma_collection, chroma_persist_dir)
            await self._chroma.initialize()

        if primary in ("faiss", "hybrid") or enable_faiss:
            self._faiss = FAISSBackend(dimension=embedding_dim)
            await self._faiss.initialize(dimension=embedding_dim)

        self._initialized = True
        logger.info(
            "Vector store initialized (primary=%s, dim=%d)",
            primary,
            embedding_dim,
        )

    async def add_document(
        self,
        doc_id: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a document to the vector store.

        In hybrid mode, writes to both backends.
        """
        tasks = []
        if self._chroma:
            tasks.append(self._chroma.add_document(doc_id, text, embedding, metadata))
        if self._faiss:
            tasks.append(self._faiss.add_document(doc_id, text, embedding, metadata))
        if tasks:
            await asyncio.gather(*tasks)

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        backend: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Search for similar documents.

        Args:
            query_embedding: Query vector.
            top_k: Number of results to return.
            filters: Metadata filters.
            backend: Override backend ("chromadb", "faiss", or None for default).

        Returns:
            List of SearchResult objects sorted by score descending.
        """
        target = backend or self._primary
        all_results: List[SearchResult] = []

        if target in ("chromadb", "hybrid") and self._chroma:
            chroma_results = await self._chroma.search(query_embedding, top_k, filters)
            all_results.extend(chroma_results)

        if target in ("faiss", "hybrid") and self._faiss:
            faiss_results = await self._faiss.search(query_embedding, top_k, filters)
            all_results.extend(faiss_results)

        if target == "hybrid":
            seen_ids = set()
            merged = []
            for r in sorted(all_results, key=lambda x: x.score, reverse=True):
                if r.document.doc_id not in seen_ids:
                    seen_ids.add(r.document.doc_id)
                    merged.append(r)
            return merged[:top_k]

        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:top_k]

    async def delete(self, doc_id: str) -> bool:
        """Delete a document from all backends."""
        success = True
        if self._chroma:
            if not await self._chroma.delete(doc_id):
                success = False
        if self._faiss:
            if not await self._faiss.delete(doc_id):
                success = False
        return success

    async def update(
        self,
        doc_id: str,
        text: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update a document in all backends."""
        success = True
        if self._chroma:
            if not await self._chroma.update(doc_id, text, embedding, metadata):
                success = False
        if self._faiss:
            if not await self._faiss.update(doc_id, text, embedding, metadata):
                success = False
        return success

    async def count(self) -> int:
        """Return the document count from the primary backend."""
        if self._chroma and self._primary in ("chromadb", "hybrid"):
            return await self._chroma.count()
        if self._faiss:
            return await self._faiss.count()
        return 0

    async def save(self, path: Optional[str] = None) -> None:
        """Save indices to disk."""
        if self._faiss:
            faiss_path = path or str(Path.home() / ".jarvis" / "data" / "faiss_index")
            await self._faiss.save(faiss_path)

    async def load(self, path: Optional[str] = None) -> None:
        """Load indices from disk."""
        if self._faiss:
            faiss_path = path or str(Path.home() / ".jarvis" / "data" / "faiss_index")
            if os.path.exists(faiss_path + ".faiss"):
                await self._faiss.load(faiss_path)

    def cleanup(self) -> None:
        """Release all resources."""
        if self._chroma:
            self._chroma.cleanup()
        if self._faiss:
            self._faiss.cleanup()
        self._initialized = False
        logger.info("Vector store cleaned up")
