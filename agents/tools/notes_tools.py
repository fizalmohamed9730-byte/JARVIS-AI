"""Notes tools for JARVIS AI agent system."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_NOTES_DIR = Path.home() / ".jarvis" / "notes"
_NOTES_DIR.mkdir(parents=True, exist_ok=True)
_NOTES_DB = _NOTES_DIR / "notes.db"


def _get_connection() -> sqlite3.Connection:
    """Get database connection with schema initialization."""
    conn = sqlite3.connect(str(_NOTES_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            tags TEXT DEFAULT '[]',
            category TEXT DEFAULT 'general',
            pinned INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_notes_category ON notes(category);
        CREATE INDEX IF NOT EXISTS idx_notes_pinned ON notes(pinned);

        CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
            title,
            content,
            tags,
            content=notes,
            content_rowid=id
        );

        CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
            INSERT INTO notes_fts(rowid, title, content, tags)
            VALUES (new.id, new.title, new.content, new.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
            INSERT INTO notes_fts(notes_fts, rowid, title, content, tags)
            VALUES ('delete', old.id, old.title, old.content, old.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
            INSERT INTO notes_fts(notes_fts, rowid, title, content, tags)
            VALUES ('delete', old.id, old.title, old.content, old.tags);
            INSERT INTO notes_fts(rowid, title, content, tags)
            VALUES (new.id, new.title, new.content, new.tags);
        END;
    """)
    conn.commit()
    return conn


def _format_note(row: sqlite3.Row) -> str:
    """Format a note for display."""
    pin = "📌 " if row["pinned"] else ""
    tags = json.loads(row["tags"]) if row["tags"] else []
    tag_str = f" [{', '.join(tags)}]" if tags else ""

    content_preview = row["content"][:200]
    if len(row["content"]) > 200:
        content_preview += "..."

    return (
        f"{pin}[{row['id']}] {row['title']}{tag_str}\n"
        f"   Category: {row['category']} | Updated: {row['updated_at'][:10]}\n"
        f"   {content_preview}\n"
    )


@tool
def create_note(
    title: str,
    content: str,
    tags: str = "",
    category: str = "general",
) -> str:
    """Create a new note.

    Args:
        title: Note title.
        content: Note content/body.
        tags: Comma-separated tags. Defaults to empty.
        category: Note category (e.g., 'work', 'personal', 'ideas'). Defaults to 'general'.

    Returns:
        A confirmation with the note ID.
    """
    if not title or not title.strip():
        return "Error: Note title is required."

    tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()] if tags else []
    now = datetime.now().isoformat()

    try:
        conn = _get_connection()
        cursor = conn.execute(
            "INSERT INTO notes (title, content, tags, category, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (title.strip(), content, json.dumps(tag_list), category.lower(), now, now),
        )
        conn.commit()
        note_id = cursor.lastrowid
        conn.close()

        return f"Note created (ID: {note_id}): {title}"

    except Exception as e:
        return f"Error creating note: {e}"


@tool
def search_notes(query: str, limit: int = 10) -> str:
    """Search notes by content or title.

    Args:
        query: Search query.
        limit: Maximum results (1-50). Defaults to 10.

    Returns:
        A formatted list of matching notes.
    """
    if not query or not query.strip():
        return "Error: Search query cannot be empty."

    limit = max(1, min(50, limit))

    try:
        conn = _get_connection()

        rows = conn.execute(
            "SELECT n.id, n.title, n.content, n.tags, n.category, n.pinned, n.created_at, n.updated_at "
            "FROM notes n "
            "JOIN notes_fts f ON n.id = f.rowid "
            "WHERE notes_fts MATCH ? "
            "ORDER BY n.pinned DESC, rank "
            "LIMIT ?",
            (query, limit),
        ).fetchall()

        if not rows:
            rows = conn.execute(
                "SELECT id, title, content, tags, category, pinned, created_at, updated_at "
                "FROM notes "
                "WHERE title LIKE ? OR content LIKE ? "
                "ORDER BY pinned DESC, updated_at DESC "
                "LIMIT ?",
                (f"%{query}%", f"%{query}%", limit),
            ).fetchall()

        conn.close()

        if not rows:
            return f"No notes found matching '{query}'."

        parts: list[str] = [f"Found {len(rows)} notes:\n"]
        for row in rows:
            parts.append(_format_note(row))

        return "\n".join(parts)

    except Exception as e:
        return f"Error searching notes: {e}"


@tool
def get_notes(category: str = "", pinned_only: bool = False) -> str:
    """Get notes filtered by category or pinned status.

    Args:
        category: Filter by category. Empty returns all.
        pinned_only: If True, only return pinned notes. Defaults to False.

    Returns:
        A formatted list of notes.
    """
    try:
        conn = _get_connection()

        conditions: list[str] = []
        params: list[Any] = []

        if category:
            conditions.append("category = ?")
            params.append(category.lower())
        if pinned_only:
            conditions.append("pinned = 1")

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        rows = conn.execute(
            f"SELECT * FROM notes {where} ORDER BY pinned DESC, updated_at DESC LIMIT 50",
            params,
        ).fetchall()
        conn.close()

        if not rows:
            return "No notes found."

        parts: list[str] = [f"Notes ({len(rows)}):\n"]
        for row in rows:
            parts.append(_format_note(row))

        return "\n".join(parts)

    except Exception as e:
        return f"Error getting notes: {e}"


@tool
def update_note(note_id: str, updates: str) -> str:
    """Update an existing note.

    Args:
        note_id: The note ID to update.
        updates: JSON string of fields to update.
            Supported: title, content, tags, category, pinned.

    Returns:
        A confirmation of the update.
    """
    if not note_id or not note_id.strip():
        return "Error: Note ID is required."

    try:
        update_data = json.loads(updates) if isinstance(updates, str) else updates
    except json.JSONDecodeError:
        return "Error: Invalid JSON in updates."

    try:
        conn = _get_connection()
        note = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not note:
            conn.close()
            return f"Error: Note {note_id} not found."

        set_clauses: list[str] = []
        params: list[Any] = []

        if "title" in update_data:
            set_clauses.append("title = ?")
            params.append(str(update_data["title"]))
        if "content" in update_data:
            set_clauses.append("content = ?")
            params.append(str(update_data["content"]))
        if "category" in update_data:
            set_clauses.append("category = ?")
            params.append(str(update_data["category"]).lower())
        if "pinned" in update_data:
            set_clauses.append("pinned = ?")
            params.append(1 if update_data["pinned"] else 0)
        if "tags" in update_data:
            tags = update_data["tags"]
            if isinstance(tags, str):
                tags = [t.strip().lower() for t in tags.split(",") if t.strip()]
            set_clauses.append("tags = ?")
            params.append(json.dumps(tags))

        if not set_clauses:
            conn.close()
            return "Error: No valid fields to update."

        set_clauses.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(note_id)

        conn.execute(f"UPDATE notes SET {', '.join(set_clauses)} WHERE id = ?", params)
        conn.commit()
        conn.close()

        return f"Note {note_id} updated."

    except Exception as e:
        return f"Error updating note: {e}"


@tool
def delete_note(note_id: str) -> str:
    """Delete a note.

    Args:
        note_id: The note ID to delete.

    Returns:
        A confirmation message.
    """
    if not note_id or not note_id.strip():
        return "Error: Note ID is required."

    try:
        conn = _get_connection()
        note = conn.execute("SELECT title FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not note:
            conn.close()
            return f"Error: Note {note_id} not found."

        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
        conn.close()

        return f"Note deleted: {note['title']}"

    except Exception as e:
        return f"Error deleting note: {e}"


notes_tools = [create_note, search_notes, get_notes, update_note, delete_note]
