"""Main LangGraph StateGraph for JARVIS AI agent system."""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.state import AgentState
from agents.graph.nodes import (
    router_node,
    conversation_node,
    task_node,
    research_node,
    coding_node,
    email_node,
    calendar_node,
    automation_node,
    memory_node,
    file_node,
    vision_node,
    notes_node,
    planner_node,
    synthesis_node,
    error_node,
    tools_node,
)
from agents.graph.edges import (
    route_intent,
    should_continue,
    check_error,
)

logger = logging.getLogger(__name__)


def build_graph() -> StateGraph:
    """Build the main JARVIS agent StateGraph."""
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("conversation_agent", conversation_node)
    graph.add_node("task_agent", task_node)
    graph.add_node("research_agent", research_node)
    graph.add_node("coding_agent", coding_node)
    graph.add_node("email_agent", email_node)
    graph.add_node("calendar_agent", calendar_node)
    graph.add_node("automation_agent", automation_node)
    graph.add_node("memory_agent", memory_node)
    graph.add_node("file_agent", file_node)
    graph.add_node("vision_agent", vision_node)
    graph.add_node("notes_agent", notes_node)
    graph.add_node("planner_agent", planner_node)
    graph.add_node("tools", tools_node)
    graph.add_node("synthesis", synthesis_node)
    graph.add_node("error", error_node)

    graph.set_entry_point("router")

    graph.add_conditional_edges(
        "router",
        route_intent,
        {
            "conversation_agent": "conversation_agent",
            "task_agent": "task_agent",
            "research_agent": "research_agent",
            "coding_agent": "coding_agent",
            "email_agent": "email_agent",
            "calendar_agent": "calendar_agent",
            "automation_agent": "automation_agent",
            "file_agent": "file_agent",
            "memory_agent": "memory_agent",
            "vision_agent": "vision_agent",
            "notes_agent": "notes_agent",
            "planner_agent": "planner_agent",
        },
    )

    agent_nodes = [
        "conversation_agent",
        "task_agent",
        "research_agent",
        "coding_agent",
        "email_agent",
        "calendar_agent",
        "automation_agent",
        "file_agent",
        "memory_agent",
        "vision_agent",
        "notes_agent",
        "planner_agent",
    ]

    for agent in agent_nodes:
        graph.add_conditional_edges(
            agent,
            should_continue,
            {
                "tools": "tools",
                "synthesize": "synthesis",
            },
        )

    graph.add_conditional_edges(
        "tools",
        check_error,
        {
            "error": "error",
            "continue": "synthesis",
        },
    )

    graph.add_edge("synthesis", END)
    graph.add_edge("error", END)

    return graph


def compile_graph() -> CompiledStateGraph:
    """Compile the main JARVIS agent graph."""
    graph = build_graph()
    compiled = graph.compile()
    logger.info("JARVIS agent graph compiled successfully")
    return compiled


main_graph = compile_graph()


async def run_jarvis(
    user_input: str,
    user_id: str = "default",
    conversation_id: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """Run the JARVIS agent graph with user input.

    Args:
        user_input: The user's message.
        user_id: User identifier.
        conversation_id: Conversation session identifier.
        **kwargs: Additional state fields.

    Returns:
        A dict with 'response', 'intent', 'error', and 'metadata'.
    """
    from agents.state import create_initial_state

    initial = create_initial_state(user_input, user_id, conversation_id)
    initial.update(kwargs)

    try:
        result = await main_graph.ainvoke(initial)

        return {
            "response": result.get("response", ""),
            "intent": result.get("intent", ""),
            "error": result.get("error"),
            "metadata": {
                "conversation_id": result.get("conversation_id", ""),
                "timestamp": result.get("timestamp", ""),
                "agent": result.get("context", {}).get("agent", ""),
            },
        }

    except Exception as e:
        logger.error("JARVIS graph execution failed: %s", e)
        return {
            "response": "I encountered an error processing your request. Please try again.",
            "intent": "",
            "error": str(e),
            "metadata": {},
        }
