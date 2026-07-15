"""
Conversation Memory for JARVIS.

Provides multiple conversation memory strategies including buffer,
summary, and knowledge graph memory with token-aware truncation
and context window management.
"""

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

APPROX_CHARS_PER_TOKEN = 4


@dataclass
class Message:
    """Represents a single conversation message."""
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )


class ConversationBufferMemory:
    """
    Stores all messages in a buffer with optional token-aware truncation.

    Simplest form of conversation memory that retains the full conversation
    history within a configurable window.
    """

    def __init__(
        self,
        max_tokens: int = 4000,
        max_messages: int = 100,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize buffer memory.

        Args:
            max_tokens: Maximum token count for the context window.
            max_messages: Maximum number of messages to retain.
            system_prompt: Optional system prompt prepended to context.
        """
        self._max_tokens = max_tokens
        self._max_messages = max_messages
        self._system_prompt = system_prompt
        self._messages: deque[Message] = deque(maxlen=max_messages)
        self._total_tokens_estimated: int = 0

    @property
    def message_count(self) -> int:
        """Return the number of stored messages."""
        return len(self._messages)

    @property
    def estimated_tokens(self) -> int:
        """Return estimated token count of stored messages."""
        return self._total_tokens_estimated

    def add_message(self, message: Message) -> None:
        """
        Add a message to the buffer.

        Trims older messages if token or message limits are exceeded.
        """
        est_tokens = len(message.content) // APPROX_CHARS_PER_TOKEN + 4
        self._messages.append(message)
        self._total_tokens_estimated += est_tokens

        while (
            self._total_tokens_estimated > self._max_tokens
            and len(self._messages) > 1
        ):
            removed = self._messages.popleft()
            self._total_tokens_estimated -= len(removed.content) // APPROX_CHARS_PER_TOKEN + 4

    def get_context(
        self,
        max_tokens: Optional[int] = None,
        include_metadata: bool = False,
    ) -> List[Dict[str, str]]:
        """
        Retrieve the conversation context.

        Args:
            max_tokens: Override the max token limit for this retrieval.
            include_metadata: Whether to include message metadata.

        Returns:
            List of message dictionaries suitable for LLM input.
        """
        limit = max_tokens or self._max_tokens
        context = []
        tokens_used = 0

        if self._system_prompt:
            system_tokens = len(self._system_prompt) // APPROX_CHARS_PER_TOKEN + 4
            context.append({"role": "system", "content": self._system_prompt})
            tokens_used += system_tokens

        messages_list = list(self._messages)
        for msg in reversed(messages_list):
            msg_tokens = len(msg.content) // APPROX_CHARS_PER_TOKEN + 4
            if tokens_used + msg_tokens > limit:
                break
            context.insert(
                -1 if self._system_prompt else 0,
                msg.to_dict() if include_metadata else {"role": msg.role, "content": msg.content},
            )
            tokens_used += msg_tokens

        return context

    def get_messages(self) -> List[Message]:
        """Return all stored messages."""
        return list(self._messages)

    def clear(self) -> None:
        """Clear all stored messages."""
        self._messages.clear()
        self._total_tokens_estimated = 0

    def get_summary(self) -> str:
        """Generate a simple summary of the conversation."""
        if not self._messages:
            return "No conversation history."

        lines = []
        for msg in self._messages:
            role = msg.role.capitalize()
            content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            lines.append(f"{role}: {content}")
        return "\n".join(lines)


class ConversationSummaryMemory:
    """
    Maintains a running summary of the conversation.

    Uses LLM-based summarization to compress conversation history
    while retaining key information.
    """

    def __init__(
        self,
        max_summary_tokens: int = 1000,
        summarize_threshold: int = 20,
        llm_callback=None,
    ):
        """
        Initialize summary memory.

        Args:
            max_summary_tokens: Maximum tokens for the stored summary.
            summarize_threshold: Number of messages before triggering summarization.
            llm_callback: Async function that takes messages and returns a summary.
        """
        self._max_summary_tokens = max_summary_tokens
        self._summarize_threshold = summarize_threshold
        self._llm_callback = llm_callback
        self._summary: str = ""
        self._recent_messages: deque[Message] = deque(maxlen=summarize_threshold)
        self._all_summaries: List[str] = []
        self._message_count: int = 0

    @property
    def message_count(self) -> int:
        """Return the total number of messages processed."""
        return self._message_count

    @property
    def summary(self) -> str:
        """Return the current conversation summary."""
        return self._summary

    async def add_message(self, message: Message) -> None:
        """
        Add a message and trigger summarization if threshold is reached.
        """
        self._recent_messages.append(message)
        self._message_count += 1

        if len(self._recent_messages) >= self._summarize_threshold:
            await self._summarize()

    async def _summarize(self) -> None:
        """Summarize recent messages and merge with existing summary."""
        messages_to_summarize = list(self._recent_messages)

        if self._llm_callback:
            try:
                prompt = self._build_summary_prompt(messages_to_summarize)
                new_summary = await self._llm_callback(prompt)
                if self._summary:
                    self._all_summaries.append(self._summary)
                self._summary = new_summary
            except Exception as e:
                logger.error("LLM summarization failed: %s", e)
                self._fallback_summarize(messages_to_summarize)
        else:
            self._fallback_summarize(messages_to_summarize)

        self._recent_messages.clear()

    def _build_summary_prompt(self, messages: List[Message]) -> str:
        """Build a prompt for LLM-based summarization."""
        parts = []
        if self._summary:
            parts.append(f"Previous summary:\n{self._summary}\n")
        parts.append("New messages to summarize:")
        for msg in messages:
            parts.append(f"{msg.role}: {msg.content}")
        parts.append("\nProvide a concise summary of the conversation including key facts, decisions, and ongoing topics.")
        return "\n".join(parts)

    def _fallback_summarize(self, messages: List[Message]) -> None:
        """Simple extractive summarization when no LLM is available."""
        key_points = []
        for msg in messages:
            content = msg.content.strip()
            if len(content) > 20:
                truncated = content[:150] + "..." if len(content) > 150 else content
                key_points.append(f"- {msg.role}: {truncated}")

        if key_points:
            new_summary = "Key points:\n" + "\n".join(key_points[-10:])
            if self._summary:
                self._summary = self._summary + "\n\n" + new_summary
            else:
                self._summary = new_summary

            summary_tokens = len(self._summary) // APPROX_CHARS_PER_TOKEN
            if summary_tokens > self._max_summary_tokens:
                lines = self._summary.split("\n")
                self._summary = "\n".join(lines[len(lines) // 2:])

    def get_context(self, max_tokens: int = 4000) -> List[Dict[str, str]]:
        """
        Get conversation context with summary and recent messages.

        Args:
            max_tokens: Maximum tokens for the context.

        Returns:
            List of message dictionaries for LLM input.
        """
        context = []
        tokens_used = 0

        if self._summary:
            summary_tokens = len(self._summary) // APPROX_CHARS_PER_TOKEN + 4
            if summary_tokens < max_tokens:
                context.append({
                    "role": "system",
                    "content": f"Conversation summary so far:\n{self._summary}",
                })
                tokens_used += summary_tokens

        for msg in reversed(self._recent_messages):
            msg_tokens = len(msg.content) // APPROX_CHARS_PER_TOKEN + 4
            if tokens_used + msg_tokens > max_tokens:
                break
            context.insert(
                1 if context and context[0]["role"] == "system" else 0,
                {"role": msg.role, "content": msg.content},
            )
            tokens_used += msg_tokens

        return context

    def clear(self) -> None:
        """Clear all memory."""
        self._summary = ""
        self._recent_messages.clear()
        self._all_summaries.clear()
        self._message_count = 0


class ConversationKnowledgeGraphMemory:
    """
    Knowledge graph-based conversation memory.

    Extracts entities and relationships from conversations to build
    a structured knowledge graph for retrieval.
    """

    def __init__(self, max_entities: int = 500):
        """
        Initialize knowledge graph memory.

        Args:
            max_entities: Maximum number of entities to track.
        """
        self._max_entities = max_entities
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._relationships: List[Dict[str, str]] = []
        self._messages: List[Message] = []
        self._entity_mentions: Dict[str, int] = {}

    @property
    def entity_count(self) -> int:
        """Return the number of tracked entities."""
        return len(self._entities)

    @property
    def relationship_count(self) -> int:
        """Return the number of tracked relationships."""
        return len(self._relationships)

    async def add_message(self, message: Message) -> None:
        """
        Process a message and extract entities and relationships.
        """
        self._messages.append(message)

        entities = self._extract_entities(message.content)
        for entity in entities:
            if entity not in self._entities:
                if len(self._entities) >= self._max_entities:
                    self._prune_least_mentioned()
                self._entities[entity] = {
                    "name": entity,
                    "first_seen": message.timestamp,
                    "last_seen": message.timestamp,
                    "context": [],
                }
                self._entity_mentions[entity] = 0

            self._entities[entity]["last_seen"] = message.timestamp
            self._entity_mentions[entity] = self._entity_mentions.get(entity, 0) + 1

            context_snippet = message.content[:200]
            if context_snippet not in self._entities[entity]["context"]:
                self._entities[entity]["context"].append(context_snippet)
                if len(self._entities[entity]["context"]) > 5:
                    self._entities[entity]["context"] = self._entities[entity]["context"][-5:]

        relationships = self._extract_relationships(message.content, entities)
        self._relationships.extend(relationships)

    def _extract_entities(self, text: str) -> List[str]:
        """
        Extract named entities from text using simple heuristics.

        Uses capitalization patterns and common entity markers.
        """
        import re

        entities = set()

        # Capitalized words (likely proper nouns)
        cap_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b')
        for match in cap_pattern.finditer(text):
            entity = match.group(1)
            if len(entity) > 1 and entity.lower() not in {
                "the", "this", "that", "what", "when", "where", "how", "why",
                "yes", "no", "please", "thanks", "hello", "hi",
            }:
                entities.add(entity)

        # Quoted strings
        quote_pattern = re.compile(r'"([^"]+)"')
        for match in quote_pattern.finditer(text):
            entities.add(match.group(1))

        return list(entities)

    def _extract_relationships(
        self, text: str, entities: List[str]
    ) -> List[Dict[str, str]]:
        """Extract relationships between co-occurring entities."""
        import re

        relationships = []
        relation_patterns = [
            (r"(\w+)\s+is\s+a\s+(\w+)", "is_a"),
            (r"(\w+)\s+works?\s+(?:at|for)\s+(\w+)", "works_at"),
            (r"(\w+)\s+knows?\s+(\w+)", "knows"),
            (r"(\w+)\s+likes?\s+(\w+)", "likes"),
            (r"(\w+)\s+prefers?\s+(\w+)", "prefers"),
            (r"(\w+)\s+lives?\s+(?:in|at|near)\s+(\w+)", "lives_in"),
        ]

        for pattern, rel_type in relation_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                relationships.append({
                    "entity1": match.group(1),
                    "entity2": match.group(2),
                    "relation": rel_type,
                    "source_text": text[:200],
                })

        if len(entities) >= 2:
            for i in range(min(len(entities), 5)):
                for j in range(i + 1, min(len(entities), 5)):
                    relationships.append({
                        "entity1": entities[i],
                        "entity2": entities[j],
                        "relation": "co_mentioned",
                        "source_text": text[:200],
                    })

        return relationships

    def _prune_least_mentioned(self) -> None:
        """Remove the least-mentioned entity to make room."""
        if not self._entity_mentions:
            return
        least = min(self._entity_mentions, key=self._entity_mentions.get)
        del self._entities[least]
        del self._entity_mentions[least]

    def get_entity(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific entity."""
        return self._entities.get(name)

    def get_entities(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all entities sorted by mention count."""
        sorted_entities = sorted(
            self._entities.values(),
            key=lambda e: self._entity_mentions.get(e["name"], 0),
            reverse=True,
        )
        return sorted_entities[:limit]

    def get_relationships(
        self,
        entity: Optional[str] = None,
        relation_type: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Get relationships, optionally filtered by entity or type."""
        results = self._relationships
        if entity:
            results = [
                r for r in results
                if r["entity1"].lower() == entity.lower()
                or r["entity2"].lower() == entity.lower()
            ]
        if relation_type:
            results = [r for r in results if r["relation"] == relation_type]
        return results

    def get_context(
        self,
        query: str,
        max_tokens: int = 2000,
    ) -> str:
        """
        Get relevant knowledge graph context for a query.

        Args:
            query: User query to match against.
            max_tokens: Maximum tokens to return.

        Returns:
            Formatted context string.
        """
        import re
        query_entities = set(re.findall(r'\b[A-Z][a-z]+\b', query))

        relevant = []
        tokens_used = 0

        for entity_name in query_entities:
            entity = self._entities.get(entity_name)
            if entity:
                entry = f"Entity: {entity['name']}"
                for ctx in entity["context"]:
                    entry += f"\n  - {ctx}"
                entry_tokens = len(entry) // APPROX_CHARS_PER_TOKEN
                if tokens_used + entry_tokens <= max_tokens:
                    relevant.append(entry)
                    tokens_used += entry_tokens

        for rel in self._relationships:
            if any(
                ent.lower() in [r["entity1"].lower(), r["entity2"].lower()]
                for ent in query_entities
                for r in [rel]
            ):
                entry = f"Relationship: {rel['entity1']} --[{rel['relation']}]--> {rel['entity2']}"
                entry_tokens = len(entry) // APPROX_CHARS_PER_TOKEN
                if tokens_used + entry_tokens <= max_tokens:
                    relevant.append(entry)
                    tokens_used += entry_tokens

        return "\n".join(relevant) if relevant else "No relevant knowledge graph data found."

    def clear(self) -> None:
        """Clear all knowledge graph data."""
        self._entities.clear()
        self._relationships.clear()
        self._messages.clear()
        self._entity_mentions.clear()


class ContextWindowManager:
    """
    Manages token-aware context window assembly from multiple memory sources.

    Combines system prompt, conversation history, knowledge graph context,
    and long-term memory into a coherent context window.
    """

    def __init__(
        self,
        max_tokens: int = 8000,
        reserved_tokens: int = 1000,
    ):
        """
        Initialize context window manager.

        Args:
            max_tokens: Maximum total tokens for the context.
            reserved_tokens: Tokens reserved for the assistant response.
        """
        self._max_tokens = max_tokens
        self._reserved_tokens = reserved_tokens
        self._available_tokens = max_tokens - reserved_tokens

    @property
    def available_tokens(self) -> int:
        """Return the number of tokens available for context."""
        return self._available_tokens

    def assemble_context(
        self,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        knowledge_context: Optional[str] = None,
        long_term_context: Optional[str] = None,
        user_query: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Assemble a complete context window from available memory sources.

        Priority: system prompt > user query > conversation > knowledge > long-term

        Args:
            system_prompt: System instructions.
            conversation_history: Recent conversation messages.
            knowledge_context: Knowledge graph context.
            long_term_context: Long-term memory context.
            user_query: Current user query.

        Returns:
            List of message dictionaries for LLM consumption.
        """
        messages = []
        tokens_used = 0

        if system_prompt:
            sp_tokens = len(system_prompt) // APPROX_CHARS_PER_TOKEN + 4
            if tokens_used + sp_tokens <= self._available_tokens:
                messages.append({"role": "system", "content": system_prompt})
                tokens_used += sp_tokens

        combined_context = ""
        if knowledge_context:
            combined_context += f"\n\nKnowledge:\n{knowledge_context}"
        if long_term_context:
            combined_context += f"\n\nLong-term memory:\n{long_term_context}"

        if combined_context:
            ctx_tokens = len(combined_context) // APPROX_CHARS_PER_TOKEN + 4
            if tokens_used + ctx_tokens <= self._available_tokens:
                if messages:
                    messages[0]["content"] += combined_context
                else:
                    messages.append({"role": "system", "content": combined_context.strip()})
                tokens_used += ctx_tokens

        if user_query:
            q_tokens = len(user_query) // APPROX_CHARS_PER_TOKEN + 4
            if tokens_used + q_tokens <= self._available_tokens:
                messages.append({"role": "user", "content": user_query})
                tokens_used += q_tokens

        if conversation_history:
            remaining = self._available_tokens - tokens_used
            recent = []
            for msg in reversed(conversation_history):
                msg_tokens = len(msg.get("content", "")) // APPROX_CHARS_PER_TOKEN + 4
                if remaining - msg_tokens < 0:
                    break
                recent.insert(0, msg)
                remaining -= msg_tokens
            for msg in recent:
                messages.insert(-1, msg) if user_query else messages.append(msg)

        return messages
