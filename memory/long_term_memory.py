"""
Long-Term Semantic Memory for JARVIS.

Provides persistent storage for facts, preferences, relationships,
and other knowledge with importance scoring and memory consolidation.
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """Represents a single long-term memory entry."""
    memory_id: str
    content: str
    category: str
    source: str
    confidence: float
    importance: float
    created_at: float
    last_accessed: float
    access_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "category": self.category,
            "source": self.source,
            "confidence": self.confidence,
            "importance": self.importance,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Create from dictionary."""
        return cls(
            memory_id=data["memory_id"],
            content=data["content"],
            category=data["category"],
            source=data.get("source", "unknown"),
            confidence=data.get("confidence", 1.0),
            importance=data.get("importance", 0.5),
            created_at=data.get("created_at", time.time()),
            last_accessed=data.get("last_accessed", time.time()),
            access_count=data.get("access_count", 0),
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
        )


class LongTermMemory:
    """
    Long-term semantic memory for persistent knowledge storage.

    Stores facts, preferences, relationships, and general knowledge
    with importance scoring, time-decay recall, and memory consolidation.
    """

    def __init__(self, auto_load: bool = True):
        self._memories: Dict[str, MemoryEntry] = {}
        self._category_index: Dict[str, List[str]] = {}
        self._entity_index: Dict[str, List[str]] = {}
        self._user_id: str = "default"
        self._auto_load = auto_load

    @property
    def memory_count(self) -> int:
        """Return the total number of stored memories."""
        return len(self._memories)

    @property
    def categories(self) -> List[str]:
        """Return all category names."""
        return list(self._category_index.keys())

    def set_user(self, user_id: str) -> None:
        """Set the active user for memory isolation."""
        self._user_id = user_id

    async def initialize(self) -> None:
        """Initialize the long-term memory, optionally loading from disk."""
        if self._auto_load:
            await self.load()

    def _default_path(self) -> Path:
        """Return the default persistence path for the active user."""
        return Path.home() / ".jarvis" / "data" / f"long_term_memory_{self._user_id}.json"

    async def save(self, path: Optional[str] = None) -> None:
        """Save all memories to a JSON file."""
        target = Path(path) if path else self._default_path()
        target.parent.mkdir(parents=True, exist_ok=True)

        def _default_handler(obj):
            if hasattr(obj, "isoformat"):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        data = {
            "user_id": self._user_id,
            "memories": {mid: entry.to_dict() for mid, entry in self._memories.items()},
            "category_index": dict(self._category_index),
            "entity_index": dict(self._entity_index),
        }

        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=_default_handler)

        logger.debug("Saved %d memories to %s", len(self._memories), target)

    async def load(self, path: Optional[str] = None) -> None:
        """Load memories from a JSON file."""
        target = Path(path) if path else self._default_path()

        if not target.exists():
            logger.debug("No memory file found at %s, starting fresh", target)
            return

        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load memories from %s: %s", target, e)
            return

        self._memories.clear()
        self._category_index.clear()
        self._entity_index.clear()

        for mid, entry_dict in data.get("memories", {}).items():
            entry = MemoryEntry.from_dict(entry_dict)
            if isinstance(entry.created_at, str):
                entry.created_at = time.time()
            if isinstance(entry.last_accessed, str):
                entry.last_accessed = time.time()
            self._memories[mid] = entry
            self._index_memory(entry)

        for cat, ids in data.get("category_index", {}).items():
            self._category_index[cat] = [mid for mid in ids if mid in self._memories]
        for entity, ids in data.get("entity_index", {}).items():
            self._entity_index[entity] = [mid for mid in ids if mid in self._memories]

        logger.info("Loaded %d memories from %s", len(self._memories), target)

    async def store_fact(
        self,
        fact: str,
        source: str = "conversation",
        confidence: float = 1.0,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a factual statement in long-term memory.

        Args:
            fact: The factual content.
            source: Where the fact was learned.
            confidence: Confidence level (0.0 to 1.0).
            importance: Importance score (0.0 to 1.0).
            metadata: Additional metadata.

        Returns:
            Memory ID string.
        """
        content_hash = self._content_hash(fact)
        for existing in self._memories.values():
            if existing.metadata.get("content_hash") == content_hash:
                existing.last_accessed = time.time()
                existing.access_count += 1
                existing.confidence = max(existing.confidence, confidence)
                logger.debug("Fact already stored, updating access: %s", existing.memory_id)
                return existing.memory_id

        memory_id = f"fact_{uuid.uuid4().hex[:12]}"
        now = time.time()
        entry = MemoryEntry(
            memory_id=memory_id,
            content=fact,
            category="fact",
            source=source,
            confidence=max(0.0, min(1.0, confidence)),
            importance=max(0.0, min(1.0, importance)),
            created_at=now,
            last_accessed=now,
            access_count=0,
            metadata={**(metadata or {}), "content_hash": content_hash, "user_id": self._user_id},
        )

        self._memories[memory_id] = entry
        self._index_memory(entry)
        logger.info("Stored fact: %s (id=%s, importance=%.2f)", fact[:60], memory_id, importance)
        asyncio.ensure_future(self.save())
        return memory_id

    async def store_preference(
        self,
        key: str,
        value: str,
        context: Optional[str] = None,
        confidence: float = 0.9,
    ) -> str:
        """
        Store a user preference.

        Args:
            key: Preference category (e.g. "theme", "language").
            value: Preference value (e.g. "dark", "English").
            context: Additional context about the preference.
            confidence: Confidence level.

        Returns:
            Memory ID string.
        """
        for existing in self._memories.values():
            if (
                existing.category == "preference"
                and existing.metadata.get("key") == key
                and existing.metadata.get("user_id") == self._user_id
            ):
                existing.content = f"User prefers {key}: {value}"
                existing.metadata["value"] = value
                existing.last_accessed = time.time()
                existing.confidence = max(existing.confidence, confidence)
                if context:
                    existing.metadata["context"] = context
                logger.info("Updated preference: %s = %s", key, value)
                return existing.memory_id

        content = f"User prefers {key}: {value}"
        if context:
            content += f" ({context})"

        memory_id = f"pref_{uuid.uuid4().hex[:12]}"
        now = time.time()
        entry = MemoryEntry(
            memory_id=memory_id,
            content=content,
            category="preference",
            source="user_interaction",
            confidence=confidence,
            importance=0.7,
            created_at=now,
            last_accessed=now,
            access_count=0,
            metadata={
                "key": key,
                "value": value,
                "context": context,
                "user_id": self._user_id,
            },
        )

        self._memories[memory_id] = entry
        self._index_memory(entry)
        logger.info("Stored preference: %s = %s", key, value)
        asyncio.ensure_future(self.save())
        return memory_id

    async def store_relationship(
        self,
        entity1: str,
        entity2: str,
        relation: str,
        confidence: float = 0.8,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a relationship between two entities.

        Args:
            entity1: First entity.
            entity2: Second entity.
            relation: Relationship type (e.g. "works_at", "knows").
            confidence: Confidence level.
            metadata: Additional metadata.

        Returns:
            Memory ID string.
        """
        content = f"{entity1} {relation} {entity2}"

        for existing in self._memories.values():
            if (
                existing.category == "relationship"
                and existing.metadata.get("entity1") == entity1
                and existing.metadata.get("entity2") == entity2
                and existing.metadata.get("relation") == relation
            ):
                existing.last_accessed = time.time()
                existing.confidence = max(existing.confidence, confidence)
                return existing.memory_id

        memory_id = f"rel_{uuid.uuid4().hex[:12]}"
        now = time.time()
        entry = MemoryEntry(
            memory_id=memory_id,
            content=content,
            category="relationship",
            source="conversation",
            confidence=confidence,
            importance=0.6,
            created_at=now,
            last_accessed=now,
            access_count=0,
            metadata={
                "entity1": entity1,
                "entity2": entity2,
                "relation": relation,
                "user_id": self._user_id,
                **(metadata or {}),
            },
        )

        self._memories[memory_id] = entry
        self._index_memory(entry)
        for entity in [entity1, entity2]:
            entity_key = entity.lower()
            if entity_key not in self._entity_index:
                self._entity_index[entity_key] = []
            if memory_id not in self._entity_index[entity_key]:
                self._entity_index[entity_key].append(memory_id)

        logger.info("Stored relationship: %s", content)
        asyncio.ensure_future(self.save())
        return memory_id

    async def recall(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        time_decay: bool = True,
        min_confidence: float = 0.3,
        embedding_manager=None,
    ) -> List[MemoryEntry]:
        """
        Recall memories relevant to a query.

        Uses keyword matching, category filtering, and optional
        embedding similarity with time decay scoring.

        Args:
            query: Search query.
            top_k: Maximum results to return.
            category: Filter by category.
            time_decay: Apply time-decay scoring.
            min_confidence: Minimum confidence threshold.
            embedding_manager: Optional EmbeddingManager for semantic search.

        Returns:
            List of relevant MemoryEntry objects sorted by score.
        """
        candidates = []

        for entry in self._memories.values():
            if entry.metadata.get("user_id") != self._user_id:
                continue
            if entry.confidence < min_confidence:
                continue
            if category and entry.category != category:
                continue
            candidates.append(entry)

        if not candidates:
            return []

        if embedding_manager and embedding_manager.is_initialized:
            return await self._semantic_recall(
                query, candidates, top_k, time_decay, embedding_manager
            )

        return self._keyword_recall(query, candidates, top_k, time_decay)

    async def _semantic_recall(
        self,
        query: str,
        candidates: List[MemoryEntry],
        top_k: int,
        time_decay: bool,
        embedding_manager,
    ) -> List[MemoryEntry]:
        """Recall using embedding similarity."""
        query_embedding = await embedding_manager.generate_embedding(query)

        scored = []
        for entry in candidates:
            if entry.metadata.get("user_id") != self._user_id:
                continue
            if entry.embedding:
                similarity = embedding_manager.cosine_similarity(query_embedding, entry.embedding)
            else:
                similarity = self._keyword_similarity(query, entry.content)

            score = similarity * entry.confidence

            if time_decay:
                age_hours = (time.time() - entry.last_accessed) / 3600
                decay = max(0.1, 1.0 / (1.0 + age_hours * 0.01))
                score *= decay

            score *= entry.importance
            scored.append((entry, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        results = [entry for entry, _ in scored[:top_k]]

        for entry in results:
            entry.last_accessed = time.time()
            entry.access_count += 1

        return results

    def _keyword_recall(
        self,
        query: str,
        candidates: List[MemoryEntry],
        top_k: int,
        time_decay: bool,
    ) -> List[MemoryEntry]:
        """Recall using keyword matching."""
        query_words = set(query.lower().split())

        scored = []
        for entry in candidates:
            if entry.metadata.get("user_id") != self._user_id:
                continue
            content_words = set(entry.content.lower().split())
            overlap = query_words & content_words
            similarity = len(overlap) / max(len(query_words), 1)

            score = similarity * entry.confidence

            if time_decay:
                age_hours = (time.time() - entry.last_accessed) / 3600
                decay = max(0.1, 1.0 / (1.0 + age_hours * 0.01))
                score *= decay

            score *= entry.importance
            scored.append((entry, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        results = [entry for entry, _ in scored[:top_k]]

        for entry in results:
            entry.last_accessed = time.time()
            entry.access_count += 1

        return results

    @staticmethod
    def _keyword_similarity(query: str, content: str) -> float:
        """Calculate simple keyword overlap similarity."""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        overlap = query_words & content_words
        return len(overlap) / max(len(query_words), 1)

    async def get_facts_about(
        self,
        entity: str,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """
        Get all facts related to a specific entity.

        Args:
            entity: Entity name to search for.
            limit: Maximum results.

        Returns:
            List of MemoryEntry objects.
        """
        entity_lower = entity.lower()
        results = []

        for entry in self._memories.values():
            if entity_lower in entry.content.lower():
                results.append(entry)

        for memory_id in self._entity_index.get(entity_lower, []):
            if memory_id in self._memories:
                entry = self._memories[memory_id]
                if entry not in results:
                    results.append(entry)

        results.sort(key=lambda e: e.importance * e.confidence, reverse=True)
        return results[:limit]

    async def get_user_profile(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Build a profile dictionary for a user from stored memories.

        Args:
            user_id: User ID. Uses active user if None.

        Returns:
            Dictionary with user profile data.
        """
        uid = user_id or self._user_id
        preferences = {}
        facts = []
        relationships = []

        for entry in self._memories.values():
            if entry.metadata.get("user_id") != uid:
                continue

            if entry.category == "preference":
                key = entry.metadata.get("key", "")
                value = entry.metadata.get("value", "")
                if key:
                    preferences[key] = value
            elif entry.category == "fact":
                facts.append(entry.content)
            elif entry.category == "relationship":
                relationships.append({
                    "entity1": entry.metadata.get("entity1", ""),
                    "entity2": entry.metadata.get("entity2", ""),
                    "relation": entry.metadata.get("relation", ""),
                })

        return {
            "user_id": uid,
            "preferences": preferences,
            "facts": facts[:50],
            "relationships": relationships[:50],
            "total_memories": len([
                e for e in self._memories.values()
                if e.metadata.get("user_id") == uid
            ]),
        }

    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        confidence: Optional[float] = None,
        importance: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update an existing memory entry.

        Args:
            memory_id: ID of the memory to update.
            content: New content.
            confidence: New confidence level.
            importance: New importance score.
            metadata: Additional metadata to merge.

        Returns:
            True if the memory was found and updated.
        """
        entry = self._memories.get(memory_id)
        if entry is None:
            return False

        if content is not None:
            entry.content = content
        if confidence is not None:
            entry.confidence = max(0.0, min(1.0, confidence))
        if importance is not None:
            entry.importance = max(0.0, min(1.0, importance))
        if metadata is not None:
            entry.metadata.update(metadata)

        entry.last_accessed = time.time()
        logger.info("Updated memory %s", memory_id)
        asyncio.ensure_future(self.save())
        return True

    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory entry.

        Args:
            memory_id: ID of the memory to delete.

        Returns:
            True if the memory was found and deleted.
        """
        entry = self._memories.pop(memory_id, None)
        if entry is None:
            return False

        self._remove_from_index(entry)
        logger.info("Deleted memory %s", memory_id)
        asyncio.ensure_future(self.save())
        return True

    async def consolidate(self, embedding_manager=None) -> int:
        """
        Consolidate similar memories by merging duplicates.

        Args:
            embedding_manager: Optional EmbeddingManager for semantic similarity.

        Returns:
            Number of memories consolidated.
        """
        to_remove = []
        consolidated = 0

        entries = list(self._memories.values())
        seen_hashes = {}

        for entry in entries:
            content_hash = self._content_hash(entry.content)
            if content_hash in seen_hashes:
                existing = seen_hashes[content_hash]
                existing.confidence = max(existing.confidence, entry.confidence)
                existing.importance = max(existing.importance, entry.importance)
                existing.access_count += entry.access_count
                to_remove.append(entry.memory_id)
                consolidated += 1
            else:
                seen_hashes[content_hash] = entry

        for memory_id in to_remove:
            entry = self._memories.pop(memory_id, None)
            if entry:
                self._remove_from_index(entry)

        if embedding_manager and embedding_manager.is_initialized:
            unique_entries = list(self._memories.values())
            if len(unique_entries) > 1:
                embeddings = await embedding_manager.batch_embed(
                    [e.content for e in unique_entries]
                )
                for entry, emb in zip(unique_entries, embeddings):
                    entry.embedding = emb

        if consolidated:
            logger.info("Consolidated %d duplicate memories", consolidated)
        return consolidated

    async def cleanup_expired(
        self,
        max_age_days: int = 365,
        min_importance: float = 0.1,
    ) -> int:
        """
        Remove old, low-importance memories.

        Args:
            max_age_days: Maximum age in days.
            min_importance: Minimum importance to keep.

        Returns:
            Number of memories removed.
        """
        cutoff = time.time() - (max_age_days * 86400)
        to_remove = []

        for memory_id, entry in self._memories.items():
            if (
                entry.last_accessed < cutoff
                and entry.importance < min_importance
                and entry.access_count < 2
            ):
                to_remove.append(memory_id)

        for memory_id in to_remove:
            entry = self._memories.pop(memory_id, None)
            if entry:
                self._remove_from_index(entry)

        if to_remove:
            logger.info("Cleaned up %d expired memories", len(to_remove))
        return len(to_remove)

    def get_stats(self) -> Dict[str, Any]:
        """Return memory statistics."""
        categories = {}
        for entry in self._memories.values():
            categories[entry.category] = categories.get(entry.category, 0) + 1

        avg_importance = 0.0
        if self._memories:
            avg_importance = sum(e.importance for e in self._memories.values()) / len(self._memories)

        return {
            "total_memories": len(self._memories),
            "categories": categories,
            "avg_importance": round(avg_importance, 3),
            "indexed_entities": len(self._entity_index),
            "user_id": self._user_id,
        }

    def _index_memory(self, entry: MemoryEntry) -> None:
        """Add a memory to category and entity indices."""
        if entry.category not in self._category_index:
            self._category_index[entry.category] = []
        if entry.memory_id not in self._category_index[entry.category]:
            self._category_index[entry.category].append(entry.memory_id)

    def _remove_from_index(self, entry: MemoryEntry) -> None:
        """Remove a memory from all indices."""
        cat_list = self._category_index.get(entry.category, [])
        if entry.memory_id in cat_list:
            cat_list.remove(entry.memory_id)

        for entity_key, mem_ids in list(self._entity_index.items()):
            if entry.memory_id in mem_ids:
                mem_ids.remove(entry.memory_id)

    @staticmethod
    def _content_hash(content: str) -> str:
        """Generate a hash for deduplication."""
        normalized = content.strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    def clear(self) -> None:
        """Clear all memories."""
        self._memories.clear()
        self._category_index.clear()
        self._entity_index.clear()
