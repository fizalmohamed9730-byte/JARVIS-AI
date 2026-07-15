"""Memory tools for JARVIS AI agent system."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_MEMORY_DIR = Path.home() / ".jarvis" / "memory"
_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
_MEMORY_DB = _MEMORY_DIR / "memories.db"


def _get_connection() -> sqlite3.Connection:
    """Get a database connection with schema initialization."""
    conn = sqlite3.connect(str(_MEMORY_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'general',
            metadata TEXT DEFAULT '{}',
            importance REAL DEFAULT 0.5,
            access_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_accessed TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
        CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);

        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            content,
            category,
            metadata,
            content=memories,
            content_rowid=id
        );

        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
            INSERT INTO memories_fts(rowid, content, category, metadata)
            VALUES (new.id, new.content, new.category, new.metadata);
        END;

        CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, content, category, metadata)
            VALUES ('delete', old.id, old.content, old.category, old.metadata);
        END;

        CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, content, category, metadata)
            VALUES ('delete', old.id, old.content, old.category, old.metadata);
            INSERT INTO memories_fts(rowid, content, category, metadata)
            VALUES (new.id, new.content, new.category, new.metadata);
        END;

        CREATE TABLE IF NOT EXISTS preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_conv_history ON conversation_history(conversation_id, timestamp);
    """)
    conn.commit()
    return conn


@tool
def store_memory(
    content: str,
    category: str = "general",
    importance: float = 0.5,
    metadata: str = "{}",
) -> str:
    """Store a new memory with optional category and metadata.

    Args:
        content: The memory content to store.
        category: Category for organizing memories (e.g., 'preference', 'fact', 'event', 'note').
            Defaults to 'general'.
        importance: Importance score from 0.0 to 1.0. Defaults to 0.5.
        metadata: JSON string of additional metadata. Defaults to '{}'.

    Returns:
        A confirmation message with the memory ID.
    """
    if not content or not content.strip():
        return "Error: Memory content cannot be empty."

    importance = max(0.0, min(1.0, importance))

    try:
        json.loads(metadata)
    except json.JSONDecodeError:
        metadata = "{}"

    now = datetime.now().isoformat()

    try:
        conn = _get_connection()
        cursor = conn.execute(
            "INSERT INTO memories (content, category, metadata, importance, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (content.strip(), category.lower(), metadata, importance, now, now),
        )
        conn.commit()
        memory_id = cursor.lastrowid
        conn.close()

        return f"Memory stored successfully (ID: {memory_id}, category: {category})"

    except Exception as e:
        return f"Error storing memory: {e}"


@tool
def search_memory(
    query: str,
    limit: int = 10,
    category: str = "",
) -> str:
    """Search memories by content.

    Args:
        query: Search query to find relevant memories.
        limit: Maximum number of results (1-50). Defaults to 10.
        category: Filter by category. Empty means all categories.

    Returns:
        A formatted list of matching memories.
    """
    if not query or not query.strip():
        return "Error: Search query cannot be empty."

    limit = max(1, min(50, limit))

    try:
        conn = _get_connection()

        if category:
            rows = conn.execute(
                "SELECT m.id, m.content, m.category, m.importance, m.created_at, m.access_count "
                "FROM memories m "
                "JOIN memories_fts f ON m.id = f.rowid "
                "WHERE memories_fts MATCH ? AND m.category = ? "
                "ORDER BY rank LIMIT ?",
                (query, category.lower(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT m.id, m.content, m.category, m.importance, m.created_at, m.access_count "
                "FROM memories m "
                "JOIN memories_fts f ON m.id = f.rowid "
                "WHERE memories_fts MATCH ? "
                "ORDER BY rank LIMIT ?",
                (query, limit),
            ).fetchall()

        if not rows:
            fallback = conn.execute(
                "SELECT id, content, category, importance, created_at, access_count "
                "FROM memories "
                "WHERE content LIKE ? "
                "ORDER BY importance DESC, created_at DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
            rows = fallback

        if not rows:
            conn.close()
            return f"No memories found matching '{query}'."

        now = datetime.now().isoformat()
        for row in rows:
            conn.execute(
                "UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
                (now, row["id"]),
            )
        conn.commit()
        conn.close()

        results: list[str] = [f"Found {len(rows)} memories:\n"]
        for row in rows:
            importance_bar = "●" * int(row["importance"] * 5) + "○" * (5 - int(row["importance"] * 5))
            results.append(
                f"- [{row['id']}] ({row['category']}) {importance_bar}\n"
                f"  {row['content']}\n"
                f"  Created: {row['created_at'][:10]} | Accessed: {row['access_count']} times\n"
            )

        return "\n".join(results)

    except Exception as e:
        return f"Error searching memories: {e}"


@tool
def get_user_preferences() -> str:
    """Get all stored user preferences.

    Returns:
        A formatted list of all stored preferences.
    """
    try:
        conn = _get_connection()
        rows = conn.execute(
            "SELECT key, value, updated_at FROM preferences ORDER BY key"
        ).fetchall()
        conn.close()

        if not rows:
            return "No preferences stored yet. Use update_preference to set some."

        parts: list[str] = [f"User Preferences ({len(rows)}):\n"]
        for row in rows:
            parts.append(f"  {row['key']}: {row['value']} (updated: {row['updated_at'][:10]})")

        return "\n".join(parts)

    except Exception as e:
        return f"Error getting preferences: {e}"


@tool
def update_preference(key: str, value: str) -> str:
    """Store or update a user preference.

    Args:
        key: Preference key (e.g., 'name', 'timezone', 'theme').
        value: Preference value.

    Returns:
        A confirmation message.
    """
    if not key or not key.strip():
        return "Error: Preference key cannot be empty."

    now = datetime.now().isoformat()

    try:
        conn = _get_connection()
        conn.execute(
            "INSERT INTO preferences (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?",
            (key.strip().lower(), value, now, value, now),
        )
        conn.commit()
        conn.close()

        return f"Preference updated: {key} = {value}"

    except Exception as e:
        return f"Error updating preference: {e}"


@tool
def get_conversation_history(conversation_id: str, limit: int = 20) -> str:
    """Retrieve conversation history for a given conversation ID.

    Args:
        conversation_id: The conversation identifier.
        limit: Maximum messages to retrieve (1-100). Defaults to 20.

    Returns:
        The conversation history as formatted messages.
    """
    if not conversation_id or not conversation_id.strip():
        return "Error: Conversation ID is required."

    limit = max(1, min(100, limit))

    try:
        conn = _get_connection()
        rows = conn.execute(
            "SELECT role, content, timestamp FROM conversation_history "
            "WHERE conversation_id = ? ORDER BY timestamp DESC LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
        conn.close()

        if not rows:
            return f"No conversation history found for '{conversation_id}'."

        rows = list(reversed(rows))

        parts: list[str] = [f"Conversation '{conversation_id}' ({len(rows)} messages):\n"]
        for row in rows:
            role_label = "You" if row["role"] == "user" else "JARVIS" if row["role"] == "assistant" else row["role"]
            parts.append(f"[{row['timestamp'][:16]}] {role_label}: {row['content']}\n")

        return "\n".join(parts)

    except Exception as e:
        return f"Error getting conversation history: {e}"


memory_tools = [
    store_memory, search_memory, get_user_preferences,
    update_preference, get_conversation_history,
]
