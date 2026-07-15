"""
Memory Manager for JARVIS.

Central orchestrator for the multi-layered memory system, coordinating
short-term conversation memory, long-term semantic memory, vector storage,
embeddings, and user profiles.
"""

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from memory.embeddings import EmbeddingManager
from memory.vector_store import VectorStoreManager, SearchResult
from memory.conversation_memory import (
    ConversationBufferMemory,
    ConversationSummaryMemory,
    ContextWindowManager,
    Message,
)
from memory.long_term_memory import LongTermMemory, MemoryEntry
from memory.user_profile import UserProfile

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Central orchestrator for the JARVIS memory system.

    Coordinates all memory layers:
    - Short-term conversation memory (buffer + summary)
    - Vector store for semantic search
    - Long-term semantic memory (facts, preferences, relationships)
    - User profile management
    """

    def __init__(self):
        self._embeddings = EmbeddingManager()
        self._vector_store = VectorStoreManager()
        self._long_term = LongTermMemory()
        self._user_profile = UserProfile()
        self._conversations: Dict[str, ConversationBufferMemory] = {}
        self._summaries: Dict[str, ConversationSummaryMemory] = {}
        self._context_manager = ContextWindowManager()
        self._initialized = False
        self._user_id: str = "default"

    @property
    def is_initialized(self) -> bool:
        """Return True if the memory system is ready."""
        return self._initialized

    @property
    def user_id(self) -> str:
        """Return the active user ID."""
        return self._user_id

    async def initialize(
        self,
        user_id: str = "default",
        embedding_backend: str = "auto",
        vector_backend: str = "chromadb",
        max_context_tokens: int = 8000,
        openai_api_key: Optional[str] = None,
    ) -> None:
        """
        Initialize all memory subsystems.

        Args:
            user_id: Active user identifier.
            embedding_backend: "online", "offline", or "auto".
            vector_backend: "chromadb", "faiss", or "hybrid".
            max_context_tokens: Maximum tokens for context windows.
            openai_api_key: Optional OpenAI API key for online embeddings.
        """
        self._user_id = user_id
        self._context_manager = ContextWindowManager(max_tokens=max_context_tokens)

        try:
            await self._embeddings.initialize(
                backend=embedding_backend,
                openai_api_key=openai_api_key,
            )
            logger.info("Embeddings initialized (%s)", self._embeddings.active_backend)
        except Exception as e:
            logger.warning("Embedding initialization failed: %s", e)

        embedding_dim = self._embeddings.embedding_dim if self._embeddings.is_initialized else 384

        try:
            await self._vector_store.initialize(
                primary=vector_backend,
                embedding_dim=embedding_dim,
            )
            logger.info("Vector store initialized (%s)", vector_backend)
        except Exception as e:
            logger.warning("Vector store initialization failed: %s", e)

        self._long_term.set_user(user_id)
        await self._long_term.initialize()
        await self._user_profile.initialize(user_id)

        self._initialized = True
        logger.info("Memory system initialized (user=%s)", user_id)

    async def add_memory(
        self,
        content: str,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        importance: float = 0.5,
        store_vector: bool = True,
    ) -> str:
        """
        Add a new memory to the system.

        Stores in long-term memory and optionally in the vector store
        for semantic search.

        Args:
            content: Memory content text.
            category: Memory category (fact, preference, general, etc.).
            metadata: Additional metadata.
            user_id: User ID override.
            importance: Importance score (0.0 to 1.0).
            store_vector: Whether to also store in vector store.

        Returns:
            Memory ID string.
        """
        uid = user_id or self._user_id

        if category == "preference":
            parts = content.split(":", 1)
            if len(parts) == 2:
                memory_id = await self._long_term.store_preference(
                    key=parts[0].strip(),
                    value=parts[1].strip(),
                    confidence=0.9,
                )
            else:
                memory_id = await self._long_term.store_fact(
                    content, confidence=0.8, importance=importance,
                    metadata={"category": category, "user_id": uid, **(metadata or {})},
                )
        elif category == "fact":
            memory_id = await self._long_term.store_fact(
                content, confidence=0.9, importance=importance,
                metadata={"user_id": uid, **(metadata or {})},
            )
        else:
            memory_id = await self._long_term.store_fact(
                content, confidence=0.7, importance=importance,
                metadata={"category": category, "user_id": uid, **(metadata or {})},
            )

        if store_vector and self._vector_store.is_initialized:
            try:
                embedding = None
                if self._embeddings.is_initialized:
                    embedding = await self._embeddings.generate_embedding(content)

                if embedding is not None:
                    await self._vector_store.add_document(
                        doc_id=memory_id,
                        text=content,
                        embedding=embedding,
                        metadata={
                            "category": category,
                            "user_id": uid,
                            "importance": importance,
                            "created_at": time.time(),
                            **(metadata or {}),
                        },
                    )
            except Exception as e:
                logger.warning("Failed to store in vector store: %s", e)

        logger.info("Memory added: %s (category=%s, id=%s)", content[:50], category, memory_id)
        return memory_id

    async def search_memory(
        self,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
        user_id: Optional[str] = None,
        use_semantic: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search across all memory stores.

        Combines vector store semantic search with long-term memory keyword search.

        Args:
            query: Search query.
            limit: Maximum results.
            category: Optional category filter.
            user_id: Optional user ID filter.
            use_semantic: Whether to use semantic (embedding) search.

        Returns:
            List of search results with scores.
        """
        all_results: List[Dict[str, Any]] = []
        seen_ids = set()

        if use_semantic and self._vector_store.is_initialized and self._embeddings.is_initialized:
            try:
                query_embedding = await self._embeddings.generate_embedding(query)
                filters = {}
                if category:
                    filters["category"] = category
                if user_id:
                    filters["user_id"] = user_id

                vector_results = await self._vector_store.search(
                    query_embedding, top_k=limit, filters=filters if filters else None,
                )
                for result in vector_results:
                    if result.document.doc_id not in seen_ids:
                        seen_ids.add(result.document.doc_id)
                        all_results.append({
                            "id": result.document.doc_id,
                            "content": result.document.text,
                            "score": result.score,
                            "metadata": result.document.metadata,
                            "source": "vector_store",
                        })
            except Exception as e:
                logger.warning("Vector search failed: %s", e)

        lt_results = await self._long_term.recall(
            query, top_k=limit, category=category,
            embedding_manager=self._embeddings if self._embeddings.is_initialized else None,
        )
        for entry in lt_results:
            if entry.memory_id not in seen_ids:
                seen_ids.add(entry.memory_id)
                all_results.append({
                    "id": entry.memory_id,
                    "content": entry.content,
                    "score": entry.importance * entry.confidence,
                    "metadata": entry.metadata,
                    "source": "long_term_memory",
                })

        all_results.sort(key=lambda r: r["score"], reverse=True)
        return all_results[:limit]

    async def get_context_window(
        self,
        conversation_id: str,
        query: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Assemble a context window for an LLM call.

        Combines conversation history, relevant long-term memories,
        and knowledge graph data.

        Args:
            conversation_id: Conversation identifier.
            query: Current user query for relevant memory retrieval.
            system_prompt: System instructions.

        Returns:
            List of message dictionaries for LLM consumption.
        """
        conversation = self._conversations.get(conversation_id)
        conv_history = conversation.get_context() if conversation else []

        knowledge_context = ""
        lt_context = ""

        if query:
            try:
                search_results = await self.search_memory(query, limit=5)
                if search_results:
                    lt_context = "\n".join(r["content"] for r in search_results[:5])
            except Exception as e:
                logger.warning("Memory search for context failed: %s", e)

        return self._context_manager.assemble_context(
            system_prompt=system_prompt,
            conversation_history=conv_history,
            knowledge_context=knowledge_context if knowledge_context else None,
            long_term_context=lt_context if lt_context else None,
            user_query=query,
        )

    def get_conversation(self, conversation_id: str) -> ConversationBufferMemory:
        """
        Get or create a conversation memory buffer.

        Args:
            conversation_id: Conversation identifier.

        Returns:
            ConversationBufferMemory instance.
        """
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = ConversationBufferMemory(
                max_tokens=4000, max_messages=200,
            )
        return self._conversations[conversation_id]

    async def add_conversation_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a message to a conversation and optionally to long-term memory.

        Args:
            conversation_id: Conversation identifier.
            role: Message role ("user" or "assistant").
            content: Message content.
            metadata: Optional metadata.
        """
        conversation = self.get_conversation(conversation_id)
        msg = Message(role=role, content=content, metadata=metadata or {})
        conversation.add_message(msg)

        if role == "user" and len(content) > 20:
            importance = min(1.0, len(content) / 200.0)
            try:
                await self.add_memory(
                    content=f"[Conversation {conversation_id[:8]}] {content[:500]}",
                    category="conversation",
                    metadata={
                        "conversation_id": conversation_id,
                        "role": role,
                        **(metadata or {}),
                    },
                    importance=importance * 0.3,
                    store_vector=True,
                )
            except Exception as e:
                logger.debug("Auto-storing conversation message failed: %s", e)

    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance: Optional[float] = None,
    ) -> bool:
        """
        Update an existing memory.

        Args:
            memory_id: Memory ID to update.
            content: New content.
            metadata: New metadata.
            importance: New importance score.

        Returns:
            True if the memory was found and updated.
        """
        success = await self._long_term.update_memory(
            memory_id, content=content, importance=importance, metadata=metadata,
        )

        if success and content and self._embeddings.is_initialized and self._vector_store.is_initialized:
            try:
                embedding = await self._embeddings.generate_embedding(content)
                await self._vector_store.update(
                    memory_id, text=content, embedding=embedding, metadata=metadata,
                )
            except Exception as e:
                logger.warning("Vector store update failed: %s", e)

        return success

    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory from all stores.

        Args:
            memory_id: Memory ID to delete.

        Returns:
            True if the memory was found and deleted.
        """
        lt_deleted = await self._long_term.delete_memory(memory_id)

        vs_deleted = True
        if self._vector_store.is_initialized:
            vs_deleted = await self._vector_store.delete(memory_id)

        return lt_deleted or vs_deleted

    async def cleanup_expired(
        self,
        max_age_days: int = 365,
        min_importance: float = 0.1,
    ) -> int:
        """
        Remove old, low-importance memories.

        Args:
            max_age_days: Maximum memory age in days.
            min_importance: Minimum importance to retain.

        Returns:
            Number of memories removed.
        """
        count = await self._long_term.cleanup_expired(max_age_days, min_importance)
        logger.info("Cleaned up %d expired memories", count)
        return count

    async def consolidate_memories(self) -> int:
        """
        Consolidate duplicate or similar memories.

        Returns:
            Number of memories consolidated.
        """
        count = await self._long_term.consolidate(
            embedding_manager=self._embeddings if self._embeddings.is_initialized else None,
        )
        logger.info("Consolidated %d memories", count)
        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive memory system statistics.

        Returns:
            Dictionary with statistics from all subsystems.
        """
        stats = {
            "user_id": self._user_id,
            "initialized": self._initialized,
            "long_term": self._long_term.get_stats(),
            "conversations": len(self._conversations),
            "embeddings": {
                "initialized": self._embeddings.is_initialized,
                "backend": self._embeddings.active_backend,
                "dimension": self._embeddings.embedding_dim,
            },
            "vector_store": {
                "initialized": self._vector_store.is_initialized,
            },
            "user_profile": self._user_profile.get_profile_summary(),
        }

        if self._vector_store.is_initialized:
            try:
                loop = asyncio.new_event_loop()
                count = loop.run_until_complete(self._vector_store.count())
                loop.close()
                stats["vector_store"]["document_count"] = count
            except Exception:
                stats["vector_store"]["document_count"] = "unknown"

        return stats

    async def store_user_preference(self, key: str, value: str) -> str:
        """
        Store a user preference across all relevant systems.

        Args:
            key: Preference key.
            value: Preference value.

        Returns:
            Memory ID.
        """
        await self._user_profile.update_preference(key, value)
        memory_id = await self._long_term.store_preference(key, value)

        if self._vector_store.is_initialized and self._embeddings.is_initialized:
            try:
                embedding = await self._embeddings.generate_embedding(
                    f"User prefers {key}: {value}"
                )
                await self._vector_store.add_document(
                    doc_id=memory_id,
                    text=f"User prefers {key}: {value}",
                    embedding=embedding,
                    metadata={"category": "preference", "key": key, "value": value},
                )
            except Exception as e:
                logger.debug("Preference vector store update failed: %s", e)

        return memory_id

    def get_user_profile(self) -> Dict[str, Any]:
        """Get the user profile summary."""
        return self._user_profile.get_profile_summary()

    def switch_user(self, user_id: str) -> None:
        """
        Switch to a different user's memory space.

        Args:
            user_id: New user identifier.
        """
        self._user_id = user_id
        self._long_term.set_user(user_id)
        logger.info("Switched to user '%s'", user_id)

    async def export_all(self, filepath: str) -> None:
        """
        Export all memory data to a file.

        Args:
            filepath: Path to write the export.
        """
        import json

        data = {
            "user_id": self._user_id,
            "stats": self.get_stats(),
            "exported_at": time.time(),
        }

        import os
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        loop = asyncio.get_event_loop()

        def _write():
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

        await loop.run_in_executor(None, _write)
        logger.info("Memory system exported to %s", filepath)

    async def cleanup(self) -> None:
        """Release all resources."""
        logger.info("Cleaning up memory system...")
        self._embeddings.cleanup()
        self._vector_store.cleanup()
        self._conversations.clear()
        self._summaries.clear()
        self._initialized = False
        logger.info("Memory system cleaned up")
