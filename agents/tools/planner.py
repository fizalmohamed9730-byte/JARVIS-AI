"""Planning agent tools for JARVIS AI agent system."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_PLANNER_DIR = Path.home() / ".jarvis" / "planner"
_PLANNER_DIR.mkdir(parents=True, exist_ok=True)
_PLANS_DB = _PLANNER_DIR / "plans.db"


def _get_connection() -> sqlite3.Connection:
    """Get database connection with schema initialization."""
    conn = sqlite3.connect(str(_PLANS_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            current_step INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS plan_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            step_order INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            dependencies TEXT DEFAULT '[]',
            estimated_time TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_steps_plan ON plan_steps(plan_id);
        CREATE INDEX IF NOT EXISTS idx_steps_status ON plan_steps(status);
    """)
    conn.commit()
    return conn


def _generate_steps_from_goal(goal: str) -> list[dict[str, str]]:
    """Generate reasonable steps from a goal using heuristic decomposition."""
    goal_lower = goal.lower()

    default_steps = [
        {"title": "Analyze and understand the goal", "description": f"Break down: {goal}"},
        {"title": "Gather necessary resources and information", "description": "Identify what is needed"},
        {"title": "Create initial approach and plan", "description": "Outline the strategy"},
        {"title": "Execute core work", "description": "Implement the main solution"},
        {"title": "Review and validate results", "description": "Check quality and completeness"},
        {"title": "Finalize and deliver", "description": "Complete the goal"},
    ]

    if any(w in goal_lower for w in ["code", "program", "develop", "build", "software"]):
        return [
            {"title": "Define requirements and specifications", "description": "Clarify what needs to be built"},
            {"title": "Design architecture and approach", "description": "Plan the technical design"},
            {"title": "Set up development environment", "description": "Prepare tools and dependencies"},
            {"title": "Implement core functionality", "description": "Write the main code"},
            {"title": "Write tests", "description": "Create test cases"},
            {"title": "Test and debug", "description": "Verify correctness"},
            {"title": "Review and refactor", "description": "Clean up code quality"},
            {"title": "Deploy and document", "description": "Ship and document"},
        ]

    if any(w in goal_lower for w in ["write", "essay", "article", "blog", "content"]):
        return [
            {"title": "Research the topic", "description": "Gather information and sources"},
            {"title": "Create outline", "description": "Structure the content"},
            {"title": "Write first draft", "description": "Compose the initial version"},
            {"title": "Revise and edit", "description": "Improve clarity and flow"},
            {"title": "Final polish and proofread", "description": "Check for errors"},
        ]

    if any(w in goal_lower for w in ["learn", "study", "understand"]):
        return [
            {"title": "Identify learning objectives", "description": "Define what to learn"},
            {"title": "Find learning resources", "description": "Gather materials"},
            {"title": "Study core concepts", "description": "Learn fundamentals"},
            {"title": "Practice with exercises", "description": "Apply knowledge"},
            {"title": "Review and consolidate", "description": "Reinforce learning"},
        ]

    if any(w in goal_lower for w in ["plan", "organize", "project"]):
        return [
            {"title": "Define scope and objectives", "description": "Clarify the goal"},
            {"title": "Identify stakeholders and resources", "description": "Map out who and what is involved"},
            {"title": "Create timeline", "description": "Set milestones and deadlines"},
            {"title": "Assign responsibilities", "description": "Delegate tasks"},
            {"title": "Monitor progress", "description": "Track and adjust as needed"},
        ]

    return default_steps


@tool
def create_plan(goal: str) -> str:
    """Break down a goal into actionable steps.

    Args:
        goal: The goal or objective to plan for.

    Returns:
        A structured plan with numbered steps.
    """
    if not goal or not goal.strip():
        return "Error: Goal cannot be empty."

    steps = _generate_steps_from_goal(goal)
    now = datetime.now().isoformat()

    try:
        conn = _get_connection()
        cursor = conn.execute(
            "INSERT INTO plans (goal, status, current_step, created_at, updated_at) "
            "VALUES (?, 'active', 0, ?, ?)",
            (goal.strip(), now, now),
        )
        plan_id = cursor.lastrowid

        for i, step in enumerate(steps):
            conn.execute(
                "INSERT INTO plan_steps (plan_id, step_order, title, description, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, 'pending', ?, ?)",
                (plan_id, i + 1, step["title"], step["description"], now, now),
            )

        conn.commit()
        conn.close()

        parts: list[str] = [f"Plan created for: {goal}\nPlan ID: {plan_id}\n\nSteps:\n"]
        for i, step in enumerate(steps, 1):
            parts.append(f"  {i}. {step['title']}")
            if step["description"]:
                parts.append(f"     {step['description']}")
        parts.append(f"\nTotal steps: {len(steps)}")

        return "\n".join(parts)

    except Exception as e:
        return f"Error creating plan: {e}"


@tool
def update_plan(plan_id: str, step_id: str, status: str) -> str:
    """Update the status of a plan step.

    Args:
        plan_id: The plan ID.
        step_id: The step order number (1-indexed).
        status: New status - 'pending', 'in_progress', 'completed', 'skipped', 'blocked'.

    Returns:
        A confirmation of the update.
    """
    if not plan_id or not step_id:
        return "Error: Plan ID and Step ID are required."

    valid_statuses = {"pending", "in_progress", "completed", "skipped", "blocked"}
    if status not in valid_statuses:
        return f"Error: Invalid status '{status}'. Use: {', '.join(sorted(valid_statuses))}"

    try:
        plan_id_int = int(plan_id)
        step_order = int(step_id)
    except ValueError:
        return "Error: Plan ID and Step ID must be numbers."

    now = datetime.now().isoformat()

    try:
        conn = _get_connection()

        plan = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id_int,)).fetchone()
        if not plan:
            conn.close()
            return f"Error: Plan {plan_id} not found."

        step = conn.execute(
            "SELECT * FROM plan_steps WHERE plan_id = ? AND step_order = ?",
            (plan_id_int, step_order),
        ).fetchone()

        if not step:
            conn.close()
            return f"Error: Step {step_id} not found in plan {plan_id}."

        conn.execute(
            "UPDATE plan_steps SET status = ?, updated_at = ? WHERE plan_id = ? AND step_order = ?",
            (status, now, plan_id_int, step_order),
        )

        if status == "completed":
            next_step = step_order + 1
            conn.execute(
                "UPDATE plans SET current_step = ?, updated_at = ? WHERE id = ?",
                (next_step, now, plan_id_int),
            )

        all_steps = conn.execute(
            "SELECT status FROM plan_steps WHERE plan_id = ? ORDER BY step_order",
            (plan_id_int,),
        ).fetchall()

        all_done = all(s["status"] in ("completed", "skipped") for s in all_steps)
        if all_done:
            conn.execute(
                "UPDATE plans SET status = 'completed', updated_at = ? WHERE id = ?",
                (now, plan_id_int),
            )

        conn.commit()
        conn.close()

        return f"Step {step_order} updated to '{status}' in plan {plan_id}."

    except Exception as e:
        return f"Error updating plan: {e}"


@tool
def get_plan(plan_id: str) -> str:
    """Get a plan with all its steps.

    Args:
        plan_id: The plan ID to retrieve.

    Returns:
        A formatted view of the plan and its steps.
    """
    if not plan_id or not plan_id.strip():
        return "Error: Plan ID is required."

    try:
        plan_id_int = int(plan_id)
    except ValueError:
        return "Error: Plan ID must be a number."

    try:
        conn = _get_connection()

        plan = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id_int,)).fetchone()
        if not plan:
            conn.close()
            return f"Error: Plan {plan_id} not found."

        steps = conn.execute(
            "SELECT * FROM plan_steps WHERE plan_id = ? ORDER BY step_order",
            (plan_id_int,),
        ).fetchall()
        conn.close()

        status_icons = {
            "pending": "⬜",
            "in_progress": "🔄",
            "completed": "✅",
            "skipped": "⏭️",
            "blocked": "🚫",
        }

        parts: list[str] = [
            f"Plan: {plan['goal']}\n"
            f"Status: {plan['status']} | Steps: {len(steps)}\n\n"
            f"Steps:\n"
        ]

        for step in steps:
            icon = status_icons.get(step["status"], "❓")
            parts.append(f"  {icon} {step['step_order']}. {step['title']} [{step['status']}]")
            if step["description"]:
                parts.append(f"     {step['description']}")

        completed = sum(1 for s in steps if s["status"] == "completed")
        total = len(steps)
        pct = int(completed / total * 100) if total > 0 else 0
        parts.append(f"\nProgress: {completed}/{total} ({pct}%)")

        return "\n".join(parts)

    except Exception as e:
        return f"Error getting plan: {e}"


@tool
def suggest_next_action(context: str = "") -> str:
    """Suggest the next action based on current context.

    Args:
        context: Current context or description of what's happening.

    Returns:
        A suggested next action.
    """
    if not context or not context.strip():
        return "Error: Context is required to suggest next actions."

    try:
        conn = _get_connection()

        active_plans = conn.execute(
            "SELECT * FROM plans WHERE status = 'active' ORDER BY updated_at DESC LIMIT 3"
        ).fetchall()

        if active_plans:
            parts: list[str] = ["Based on your active plans:\n"]
            for plan in active_plans:
                current_step = conn.execute(
                    "SELECT * FROM plan_steps WHERE plan_id = ? AND status != 'completed' AND status != 'skipped' "
                    "ORDER BY step_order LIMIT 1",
                    (plan["id"],),
                ).fetchone()

                if current_step:
                    parts.append(
                        f"Plan: {plan['goal'][:60]}\n"
                        f"  Next step: {current_step['title']}\n"
                        f"  {current_step['description']}\n"
                    )
                else:
                    parts.append(f"Plan '{plan['goal'][:60]}': All steps completed! Review results.\n")

            conn.close()
            return "\n".join(parts)

        context_lower = context.lower()
        suggestions: list[str] = []

        if any(w in context_lower for w in ["stuck", "problem", "error", "issue", "bug"]):
            suggestions = [
                "Break the problem into smaller parts and test each one",
                "Search for similar problems online",
                "Review error messages carefully for clues",
                "Try a different approach or algorithm",
                "Ask for help or check documentation",
            ]
        elif any(w in context_lower for w in ["start", "begin", "new", "first"]):
            suggestions = [
                "Define clear objectives and success criteria",
                "Gather all necessary resources and information",
                "Break the task into smaller, manageable steps",
                "Set up your working environment",
                "Start with the most critical or foundational piece",
            ]
        elif any(w in context_lower for w in ["finish", "done", "complete", "close"]):
            suggestions = [
                "Review the work for completeness and quality",
                "Document what was done and any decisions made",
                "Clean up temporary files and resources",
                "Share results with relevant stakeholders",
                "Note lessons learned for future reference",
            ]
        else:
            suggestions = [
                "Review current priorities and align with goals",
                "Identify blockers and address them first",
                "Focus on the highest-impact task first",
                "Set a specific time block for focused work",
                "Take breaks to maintain productivity",
            ]

        conn.close()

        parts: list[str] = ["Suggested next actions:\n"]
        for i, s in enumerate(suggestions, 1):
            parts.append(f"  {i}. {s}")

        return "\n".join(parts)

    except Exception as e:
        return f"Error suggesting next action: {e}"


planner_tools = [create_plan, update_plan, get_plan, suggest_next_action]
