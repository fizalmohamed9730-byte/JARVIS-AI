"""Task management tools for JARVIS AI agent system."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_TASKS_DIR = Path.home() / ".jarvis" / "tasks"
_TASKS_DIR.mkdir(parents=True, exist_ok=True)
_TASKS_DB = _TASKS_DIR / "tasks.db"


def _get_connection() -> sqlite3.Connection:
    """Get database connection with schema initialization."""
    conn = sqlite3.connect(str(_TASKS_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            priority TEXT NOT NULL DEFAULT 'medium',
            due_date TEXT,
            completed_at TEXT,
            tags TEXT DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
        CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date);
    """)
    conn.commit()
    return conn


def _format_task(task: sqlite3.Row) -> str:
    """Format a task row for display."""
    priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    status_icons = {"pending": "⏳", "in_progress": "🔄", "completed": "✅", "cancelled": "❌"}

    icon = priority_icons.get(task["priority"], "⚪")
    status_icon = status_icons.get(task["status"], "❓")

    lines = [
        f"{status_icon} {icon} [{task['id']}] {task['title']}",
        f"   Status: {task['status']} | Priority: {task['priority']}",
    ]
    if task["description"]:
        lines.append(f"   {task['description'][:100]}")
    if task["due_date"]:
        lines.append(f"   Due: {task['due_date']}")
    return "\n".join(lines)


@tool
def create_task(
    title: str,
    description: str = "",
    priority: str = "medium",
    due_date: str = "",
    tags: str = "",
) -> str:
    """Create a new task.

    Args:
        title: Task title/name.
        description: Detailed description. Defaults to empty.
        priority: Priority level - 'high', 'medium', or 'low'. Defaults to 'medium'.
        due_date: Due date in format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM'. Defaults to empty.
        tags: Comma-separated tags for categorization. Defaults to empty.

    Returns:
        A confirmation with the task details.
    """
    if not title or not title.strip():
        return "Error: Task title is required."

    priority = priority.lower().strip()
    if priority not in ("high", "medium", "low"):
        priority = "medium"

    if due_date and due_date.strip():
        parsed = _parse_task_date(due_date.strip())
        if not parsed:
            return f"Error: Could not parse due date '{due_date}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM"
        due_date = parsed.strftime("%Y-%m-%d %H:%M")
    else:
        due_date = None

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    now = datetime.now().isoformat()

    try:
        conn = _get_connection()
        cursor = conn.execute(
            "INSERT INTO tasks (title, description, priority, due_date, tags, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title.strip(), description.strip(), priority, due_date, json.dumps(tag_list), now, now),
        )
        conn.commit()
        task_id = cursor.lastrowid
        conn.close()

        return f"Task created (ID: {task_id}):\n  Title: {title}\n  Priority: {priority}" + (f"\n  Due: {due_date}" if due_date else "")

    except Exception as e:
        return f"Error creating task: {e}"


@tool
def update_task(task_id: str, updates: str) -> str:
    """Update an existing task.

    Args:
        task_id: The task ID to update.
        updates: JSON string of fields to update.
            Supported: title, description, status, priority, due_date, tags.
            Status values: pending, in_progress, completed, cancelled.

    Returns:
        A confirmation of the update.
    """
    if not task_id or not task_id.strip():
        return "Error: Task ID is required."

    try:
        update_data = json.loads(updates) if isinstance(updates, str) else updates
    except json.JSONDecodeError:
        return "Error: Invalid JSON in updates."

    try:
        conn = _get_connection()
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not task:
            conn.close()
            return f"Error: Task {task_id} not found."

        set_clauses: list[str] = []
        params: list[Any] = []

        for field in ("title", "description", "priority", "status"):
            if field in update_data:
                set_clauses.append(f"{field} = ?")
                params.append(str(update_data[field]))

        if "due_date" in update_data:
            val = update_data["due_date"]
            if val:
                parsed = _parse_task_date(str(val))
                if parsed:
                    set_clauses.append("due_date = ?")
                    params.append(parsed.strftime("%Y-%m-%d %H:%M"))
            else:
                set_clauses.append("due_date = NULL")

        if "tags" in update_data:
            tags = update_data["tags"]
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            set_clauses.append("tags = ?")
            params.append(json.dumps(tags))

        if update_data.get("status") == "completed":
            set_clauses.append("completed_at = ?")
            params.append(datetime.now().isoformat())

        if not set_clauses:
            conn.close()
            return "Error: No valid fields to update."

        set_clauses.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(task_id)

        conn.execute(
            f"UPDATE tasks SET {', '.join(set_clauses)} WHERE id = ?",
            params,
        )
        conn.commit()

        updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        conn.close()

        return f"Task updated:\n{_format_task(updated)}"

    except Exception as e:
        return f"Error updating task: {e}"


@tool
def get_tasks(
    status: str = "",
    priority: str = "",
    date_range: str = "",
    limit: int = 50,
) -> str:
    """Get tasks filtered by status, priority, or date range.

    Args:
        status: Filter by status ('pending', 'in_progress', 'completed', 'cancelled').
            Empty returns all.
        priority: Filter by priority ('high', 'medium', 'low'). Empty returns all.
        date_range: Filter by due date range ('today', 'week', 'overdue').
            Empty returns all.
        limit: Maximum tasks to return (1-100). Defaults to 50.

    Returns:
        A formatted list of matching tasks.
    """
    limit = max(1, min(100, limit))

    try:
        conn = _get_connection()

        conditions: list[str] = []
        params: list[Any] = []

        if status:
            conditions.append("status = ?")
            params.append(status.lower())
        if priority:
            conditions.append("priority = ?")
            params.append(priority.lower())

        now = datetime.now()
        if date_range.lower() == "today":
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d")
            today_end = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d")
            conditions.append("due_date >= ? AND due_date < ?")
            params.extend([today_start, today_end])
        elif date_range.lower() == "week":
            week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start -= timedelta(days=week_start.weekday())
            week_end = week_start + timedelta(days=7)
            conditions.append("due_date >= ? AND due_date < ?")
            params.extend([week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d")])
        elif date_range.lower() == "overdue":
            conditions.append("due_date < ? AND status != 'completed' AND status != 'cancelled'")
            params.append(now.strftime("%Y-%m-%d %H:%M"))

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        rows = conn.execute(
            f"SELECT * FROM tasks {where} ORDER BY "
            "CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, "
            "due_date ASC NULLS LAST "
            "LIMIT ?",
            params + [limit],
        ).fetchall()
        conn.close()

        if not rows:
            return "No tasks found matching the criteria."

        parts: list[str] = [f"Tasks ({len(rows)}):\n"]
        for row in rows:
            parts.append(_format_task(row))
            parts.append("")

        return "\n".join(parts)

    except Exception as e:
        return f"Error getting tasks: {e}"


@tool
def complete_task(task_id: str) -> str:
    """Mark a task as completed.

    Args:
        task_id: The task ID to complete.

    Returns:
        A confirmation message.
    """
    if not task_id or not task_id.strip():
        return "Error: Task ID is required."

    try:
        conn = _get_connection()
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not task:
            conn.close()
            return f"Error: Task {task_id} not found."

        if task["status"] == "completed":
            conn.close()
            return f"Task {task_id} is already completed."

        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE tasks SET status = 'completed', completed_at = ?, updated_at = ? WHERE id = ?",
            (now, now, task_id),
        )
        conn.commit()
        conn.close()

        return f"Task completed: {task['title']}"

    except Exception as e:
        return f"Error completing task: {e}"


@tool
def get_today_tasks() -> str:
    """Get all tasks due today.

    Returns:
        A formatted list of today's tasks.
    """
    try:
        conn = _get_connection()
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d")
        today_end = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d")

        rows = conn.execute(
            "SELECT * FROM tasks WHERE due_date >= ? AND due_date < ? "
            "AND status != 'completed' AND status != 'cancelled' "
            "ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END",
            (today_start, today_end),
        ).fetchall()

        all_today = conn.execute(
            "SELECT * FROM tasks WHERE due_date >= ? AND due_date < ? "
            "ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END",
            (today_start, today_end),
        ).fetchall()
        conn.close()

        if not all_today:
            return "No tasks for today."

        pending = [r for r in all_today if r["status"] not in ("completed", "cancelled")]
        completed = [r for r in all_today if r["status"] == "completed"]

        parts: list[str] = []
        if pending:
            parts.append(f"Today's Tasks ({len(pending)} pending):\n")
            for row in pending:
                parts.append(_format_task(row))
                parts.append("")
        if completed:
            parts.append(f"\nCompleted Today ({len(completed)}):\n")
            for row in completed:
                parts.append(_format_task(row))
                parts.append("")

        return "\n".join(parts)

    except Exception as e:
        return f"Error getting today's tasks: {e}"


@tool
def get_overdue_tasks() -> str:
    """Get all overdue tasks that are not completed.

    Returns:
        A formatted list of overdue tasks sorted by priority.
    """
    try:
        conn = _get_connection()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        rows = conn.execute(
            "SELECT * FROM tasks WHERE due_date < ? "
            "AND status != 'completed' AND status != 'cancelled' "
            "ORDER BY due_date ASC, "
            "CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END",
            (now,),
        ).fetchall()
        conn.close()

        if not rows:
            return "No overdue tasks."

        parts: list[str] = [f"Overdue Tasks ({len(rows)}):\n"]
        for row in rows:
            parts.append(_format_task(row))
            parts.append("")

        return "\n".join(parts)

    except Exception as e:
        return f"Error getting overdue tasks: {e}"


def _parse_task_date(date_str: str) -> Optional[datetime]:
    """Parse a task date string."""
    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


task_tools = [
    create_task, update_task, get_tasks, complete_task,
    get_today_tasks, get_overdue_tasks,
]
