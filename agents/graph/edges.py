"""Edge functions for the JARVIS AI agent graph."""

from __future__ import annotations

import logging
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage

from agents.state import AgentState

logger = logging.getLogger(__name__)


def route_intent(state: AgentState) -> str:
    """Route to the correct agent based on classified intent.

    Reads state['intent'] and returns the corresponding node name.
    """
    intent = state.get("intent", "general")

    intent_to_node: dict[str, str] = {
        "conversation": "conversation_agent",
        "task": "task_agent",
        "research": "research_agent",
        "coding": "coding_agent",
        "email": "email_agent",
        "calendar": "calendar_agent",
        "automation": "automation_agent",
        "file": "file_agent",
        "memory": "memory_agent",
        "vision": "vision_agent",
        "notes": "notes_agent",
        "planning": "planner_agent",
        "general": "conversation_agent",
    }

    node = intent_to_node.get(intent, "conversation_agent")
    logger.info("Routing intent '%s' to node '%s'", intent, node)
    return node


def should_continue(state: AgentState) -> str:
    """Check if the agent needs more tool calls or should synthesize.

    Returns 'tools' if there are pending tool calls, 'synthesize' otherwise.
    """
    messages = state.get("messages", [])

    if messages and isinstance(messages[-1], AIMessage):
        last_msg = messages[-1]
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            return "tools"

    return "synthesize"


def check_memory(state: AgentState) -> str:
    """Determine if a memory lookup is needed before processing.

    Returns 'memory_lookup' if relevant context should be fetched,
    'process' to proceed directly.
    """
    user_input = state.get("user_input", "").lower()

    memory_keywords = {
        "remember", "recall", "previously", "before", "last time",
        "earlier", "history", "past", "forgot", "memory",
        "what did i", "when did i", "did i tell you",
    }

    for keyword in memory_keywords:
        if keyword in user_input:
            return "memory_lookup"

    context = state.get("context", {})
    if context.get("requires_memory_context"):
        return "memory_lookup"

    return "process"


def should_store_memory(state: AgentState) -> Literal["store", "skip"]:
    """Determine if the conversation should be stored in memory."""
    user_input = state.get("user_input", "").lower()

    skip_keywords = {"hi", "hello", "hey", "thanks", "ok", "yes", "no"}
    if user_input.strip() in skip_keywords:
        return "skip"

    important_keywords = {
        "remember", "important", "always", "never", "prefer",
        "my name", "i am", "i'm", "i like", "i need",
        "password", "account", "address", "phone",
    }

    for keyword in important_keywords:
        if keyword in user_input:
            return "store"

    return "store"


def check_error(state: AgentState) -> Literal["error", "continue"]:
    """Check if an error occurred and needs handling."""
    if state.get("error"):
        return "error"
    return "continue"
