"""Graph node implementations for JARVIS AI agent system."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.language_models import BaseChatModel

from agents.state import AgentState
from agents.tools import (
    CONVERSATION_TOOLS,
    TASK_TOOLS,
    RESEARCH_TOOLS,
    CODING_TOOLS,
    EMAIL_TOOLS,
    CALENDAR_TOOLS,
    AUTOMATION_TOOLS,
    FILE_TOOLS,
    MEMORY_TOOLS,
    VISION_TOOLS,
    NOTES_TOOLS,
    PLANNER_TOOLS,
    ALL_TOOLS,
)

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """You are JARVIS intent classifier. Given a user message, classify the intent.

Respond with ONLY a JSON object (no markdown, no extra text):
{"intent": "<intent>", "confidence": <0.0-1.0>, "sub_intent": "<optional detail>"}

Available intents:
- conversation: General chat, greetings, questions about JARVIS
- task: Create, update, view, or complete tasks/todos
- research: Web search, information gathering, fact-finding
- coding: Code explanation, generation, debugging, programming help
- email: Read, send, reply to, or search emails
- calendar: Schedule, view, update, or delete events/appointments
- automation: Open/close apps, system commands, volume, brightness
- file: Search, read, create, move, delete files
- memory: Store or recall personal information and preferences
- vision: Image analysis, OCR, screenshots
- notes: Create, search, update notes
- planning: Create plans, break goals into steps

Be decisive. Choose the single most relevant intent."""


def _get_llm() -> BaseChatModel:
    """Get the configured LLM instance."""
    from config import get_llm as _get_llm_instance
    return _get_llm_instance()


def _get_llm_with_tools(tools: list) -> BaseChatModel:
    """Get LLM bound to specific tools."""
    llm = _get_llm()
    return llm.bind_tools(tools)


async def router_node(state: AgentState) -> dict[str, Any]:
    """Classify user intent and route to the appropriate agent."""
    user_input = state.get("user_input", "")
    if not user_input:
        return {
            "intent": "conversation",
            "context": {**state.get("context", {}), "router_confidence": 1.0},
        }

    try:
        llm = _get_llm()
        messages = [
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=user_input),
        ]

        response = await llm.ainvoke(messages)
        content = response.content.strip()

        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        parsed = json.loads(content)
        intent = parsed.get("intent", "general")
        confidence = parsed.get("confidence", 0.8)
        sub_intent = parsed.get("sub_intent", "")

        valid_intents = {
            "conversation", "task", "research", "coding", "email",
            "calendar", "automation", "file", "memory", "vision",
            "notes", "planning", "general",
        }
        if intent not in valid_intents:
            intent = "general"

        return {
            "intent": intent,
            "context": {
                **state.get("context", {}),
                "router_confidence": confidence,
                "router_sub_intent": sub_intent,
            },
        }

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning("Router parsing failed: %s. Defaulting to conversation.", e)
        return {
            "intent": "conversation",
            "context": {**state.get("context", {}), "router_error": str(e)},
        }
    except Exception as e:
        logger.error("Router node error: %s", e)
        return {
            "intent": "general",
            "error": str(e),
        }


async def conversation_node(state: AgentState) -> dict[str, Any]:
    """Handle general conversation with memory context."""
    user_input = state.get("user_input", "")
    messages = list(state.get("messages", []))
    memory = state.get("memory", {})

    system_parts = [
        "You are JARVIS, a helpful and intelligent AI personal assistant.",
        "Be concise, accurate, and proactive in your responses.",
        "Use a professional but friendly tone.",
    ]

    if memory.get("user_preferences"):
        system_parts.append(f"User preferences: {json.dumps(memory['user_preferences'])}")

    if memory.get("recent_memories"):
        system_parts.append(f"Relevant memories: {json.dumps(memory['recent_memories'][:3])}")

    system_msg = SystemMessage(content="\n".join(system_parts))
    all_messages = [system_msg] + messages + [HumanMessage(content=user_input)]

    try:
        llm = _get_llm_with_tools(CONVERSATION_TOOLS)
        response = await llm.ainvoke(all_messages)

        new_messages = messages + [HumanMessage(content=user_input), response]
        return {
            "messages": new_messages,
            "response": response.content,
            "context": {**state.get("context", {}), "agent": "conversation"},
        }

    except Exception as e:
        logger.error("Conversation node error: %s", e)
        return {
            "error": str(e),
            "response": "I encountered an error. Please try again.",
        }


async def task_node(state: AgentState) -> dict[str, Any]:
    """Handle task management operations."""
    user_input = state.get("user_input", "")
    messages = list(state.get("messages", []))

    system_msg = SystemMessage(
        content=(
            "You are JARVIS task manager. Help the user create, update, view, "
            "and complete tasks. Use the task tools to interact with the task system. "
            "Always confirm what action was taken."
        )
    )
    all_messages = [system_msg] + messages + [HumanMessage(content=user_input)]

    try:
        llm = _get_llm_with_tools(TASK_TOOLS)
        response = await llm.ainvoke(all_messages)

        new_messages = messages + [HumanMessage(content=user_input), response]
        return {
            "messages": new_messages,
            "response": response.content,
            "context": {**state.get("context", {}), "agent": "task"},
        }

    except Exception as e:
        logger.error("Task node error: %s", e)
        return {"error": str(e), "response": "Error managing tasks."}


async def research_node(state: AgentState) -> dict[str, Any]:
    """Handle research and information gathering."""
    user_input = state.get("user_input", "")
    messages = list(state.get("messages", []))

    system_msg = SystemMessage(
        content=(
            "You are JARVIS research assistant. Search the web and gather information "
            "to answer the user's questions. Use web_search and fetch_webpage tools. "
            "Always cite your sources. Be thorough but concise."
        )
    )
    all_messages = [system_msg] + messages + [HumanMessage(content=user_input)]

    try:
        llm = _get_llm_with_tools(RESEARCH_TOOLS)
        response = await llm.ainvoke(all_messages)

        new_messages = messages + [HumanMessage(content=user_input), response]
        return {
            "messages": new_messages,
            "response": response.content,
            "context": {**state.get("context", {}), "agent": "research"},
        }

    except Exception as e:
        logger.error("Research node error: %s", e)
        return {"error": str(e), "response": "Error during research."}


async def coding_node(state: AgentState) -> dict[str, Any]:
    """Handle coding-related tasks."""
    user_input = state.get("user_input", "")
    messages = list(state.get("messages", []))

    system_msg = SystemMessage(
        content=(
            "You are JARVIS coding assistant. Help with code explanation, generation, "
            "debugging, and programming questions. Use code blocks with proper language tags. "
            "Be precise and follow best practices. You can also read/write files."
        )
    )
    all_messages = [system_msg] + messages + [HumanMessage(content=user_input)]

    try:
        llm = _get_llm_with_tools(CODING_TOOLS)
        response = await llm.ainvoke(all_messages)

        new_messages = messages + [HumanMessage(content=user_input), response]
        return {
            "messages": new_messages,
            "response": response.content,
            "context": {**state.get("context", {}), "agent": "coding"},
        }

    except Exception as e:
        logger.error("Coding node error: %s", e)
        return {"error": str(e), "response": "Error with coding task."}


async def email_node(state: AgentState) -> dict[str, Any]:
    """Handle email operations."""
    user_input = state.get("user_input", "")
    messages = list(state.get("messages", []))

    system_msg = SystemMessage(
        content=(
            "You are JARVIS email assistant. Help read, send, reply to, and search emails. "
            "Use the email tools to perform operations. Always confirm actions before sending. "
            "Be professional in email communications."
        )
    )
    all_messages = [system_msg] + messages + [HumanMessage(content=user_input)]

    try:
        llm = _get_llm_with_tools(EMAIL_TOOLS)
        response = await llm.ainvoke(all_messages)

        new_messages = messages + [HumanMessage(content=user_input), response]
        return {
            "messages": new_messages,
            "response": response.content,
            "context": {**state.get("context", {}), "agent": "email"},
        }

    except Exception as e:
        logger.error("Email node error: %s", e)
        return {"error": str(e), "response": "Error with email operations."}


async def calendar_node(state: AgentState) -> dict[str, Any]:
    """Handle calendar operations."""
    user_input = state.get("user_input", "")
    messages = list(state.get("messages", []))

    system_msg = SystemMessage(
        content=(
            "You are JARVIS calendar assistant. Help schedule, view, update, and manage "
            "events and appointments. Use calendar tools. Be mindful of conflicts and "
            "suggest optimal times."
        )
    )
    all_messages = [system_msg] + messages + [HumanMessage(content=user_input)]

    try:
        llm = _get_llm_with_tools(CALENDAR_TOOLS)
        response = await llm.ainvoke(all_messages)

        new_messages = messages + [HumanMessage(content=user_input), response]
        return {
            "messages": new_messages,
            "response": response.content,
            "context": {**state.get("context", {}), "agent": "calendar"},
        }

    except Exception as e:
        logger.error("Calendar node error: %s", e)
        return {"error": str(e), "response": "Error with calendar operations."}


async def automation_node(state: AgentState) -> dict[str, Any]:
    """Handle system automation commands."""
    user_input = state.get("user_input", "")
    messages = list(state.get("messages", []))

    system_msg = SystemMessage(
        content=(
            "You are JARVIS system automation assistant. Help open/close applications, "
            "control volume/brightness, run system commands, open websites, and take "
            "screenshots. Always confirm actions before executing potentially impactful commands."
        )
    )
    all_messages = [system_msg] + messages + [HumanMessage(content=user_input)]

    try:
        llm = _get_llm_with_tools(AUTOMATION_TOOLS)
        response = await llm.ainvoke(all_messages)

        new_messages = messages + [HumanMessage(content=user_input), response]
        return {
            "messages": new_messages,
            "response": response.content,
            "context": {**state.get("context", {}), "agent": "automation"},
        }

    except Exception as e:
        logger.error("Automation node error: %s", e)
        return {"error": str(e), "response": "Error with automation."}


async def memory_node(state: AgentState) -> dict[str, Any]:
    """Handle memory storage and retrieval."""
    user_input = state.get("user_input", "")
    messages = list(state.get("messages", []))

    system_msg = SystemMessage(
        content=(
            "You are JARVIS memory assistant. Help store, retrieve, and manage personal "
            "memories and preferences. Use memory tools. Be thoughtful about what to remember."
        )
    )
    all_messages = [system_msg] + messages + [HumanMessage(content=user_input)]

    try:
        llm = _get_llm_with_tools(MEMORY_TOOLS)
        response = await llm.ainvoke(all_messages)

        new_messages = messages + [HumanMessage(content=user_input), response]
        return {
            "messages": new_messages,
            "response": response.content,
            "context": {**state.get("context", {}), "agent": "memory"},
        }

    except Exception as e:
        logger.error("Memory node error: %s", e)
        return {"error": str(e), "response": "Error with memory operations."}


async def file_node(state: AgentState) -> dict[str, Any]:
    """Handle file operations."""
    user_input = state.get("user_input", "")
    messages = list(state.get("messages", []))

    system_msg = SystemMessage(
        content=(
            "You are JARVIS file assistant. Help search, read, create, move, and delete "
            "files. Use file tools. Be careful with destructive operations and always confirm."
        )
    )
    all_messages = [system_msg] + messages + [HumanMessage(content=user_input)]

    try:
        llm = _get_llm_with_tools(FILE_TOOLS)
        response = await llm.ainvoke(all_messages)

        new_messages = messages + [HumanMessage(content=user_input), response]
        return {
            "messages": new_messages,
            "response": response.content,
            "context": {**state.get("context", {}), "agent": "file"},
        }

    except Exception as e:
        logger.error("File node error: %s", e)
        return {"error": str(e), "response": "Error with file operations."}


async def vision_node(state: AgentState) -> dict[str, Any]:
    """Handle vision and image analysis tasks."""
    user_input = state.get("user_input", "")
    messages = list(state.get("messages", []))

    system_msg = SystemMessage(
        content=(
            "You are JARVIS vision assistant. Help analyze images, extract text via OCR, "
            "capture webcam images, and analyze screenshots. Use vision tools."
        )
    )
    all_messages = [system_msg] + messages + [HumanMessage(content=user_input)]

    try:
        llm = _get_llm_with_tools(VISION_TOOLS)
        response = await llm.ainvoke(all_messages)

        new_messages = messages + [HumanMessage(content=user_input), response]
        return {
            "messages": new_messages,
            "response": response.content,
            "context": {**state.get("context", {}), "agent": "vision"},
        }

    except Exception as e:
        logger.error("Vision node error: %s", e)
        return {"error": str(e), "response": "Error with vision operations."}


async def notes_node(state: AgentState) -> dict[str, Any]:
    """Handle notes operations."""
    user_input = state.get("user_input", "")
    messages = list(state.get("messages", []))

    system_msg = SystemMessage(
        content=(
            "You are JARVIS notes assistant. Help create, search, update, and organize "
            "notes. Use notes tools. Help the user keep their thoughts organized."
        )
    )
    all_messages = [system_msg] + messages + [HumanMessage(content=user_input)]

    try:
        llm = _get_llm_with_tools(NOTES_TOOLS)
        response = await llm.ainvoke(all_messages)

        new_messages = messages + [HumanMessage(content=user_input), response]
        return {
            "messages": new_messages,
            "response": response.content,
            "context": {**state.get("context", {}), "agent": "notes"},
        }

    except Exception as e:
        logger.error("Notes node error: %s", e)
        return {"error": str(e), "response": "Error with notes operations."}


async def planner_node(state: AgentState) -> dict[str, Any]:
    """Handle planning and goal decomposition."""
    user_input = state.get("user_input", "")
    messages = list(state.get("messages", []))

    system_msg = SystemMessage(
        content=(
            "You are JARVIS planning assistant. Help break down goals into actionable steps, "
            "create plans, and suggest next actions. Use planner tools to manage plans."
        )
    )
    all_messages = [system_msg] + messages + [HumanMessage(content=user_input)]

    try:
        llm = _get_llm_with_tools(PLANNER_TOOLS)
        response = await llm.ainvoke(all_messages)

        new_messages = messages + [HumanMessage(content=user_input), response]
        return {
            "messages": new_messages,
            "response": response.content,
            "context": {**state.get("context", {}), "agent": "planning"},
        }

    except Exception as e:
        logger.error("Planner node error: %s", e)
        return {"error": str(e), "response": "Error with planning."}


async def synthesis_node(state: AgentState) -> dict[str, Any]:
    """Synthesize final response from agent output.

    If the agent returned tool calls (no text content), re-invoke the LLM
    with the full message history to produce a natural-language summary.
    """
    response = state.get("response", "")

    if not response:
        messages = state.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
                response = msg.content
                break

    if not response and state.get("messages"):
        try:
            llm = _get_llm()
            summary_prompt = [
                SystemMessage(
                    content=(
                        "You are JARVIS. The user's request has been processed by tools. "
                        "Based on the tool results below, provide a clear, helpful, "
                        "natural-language response to the user."
                    )
                ),
                *state["messages"],
                HumanMessage(content="Please summarize the results of the tool operations above."),
            ]
            ai_response = await llm.ainvoke(summary_prompt)
            response = ai_response.content
        except Exception as e:
            logger.error("Synthesis LLM fallback failed: %s", e)

    if not response:
        response = "I'm not sure how to help with that. Could you rephrase your request?"

    return {
        "response": response,
        "timestamp": datetime.now().isoformat(),
    }


async def error_node(state: AgentState) -> dict[str, Any]:
    """Handle errors gracefully."""
    error = state.get("error", "Unknown error")

    logger.error("Agent error: %s", error)

    user_friendly = (
        "I encountered an issue while processing your request. "
        "Please try again, or rephrase your request if the problem persists."
    )

    return {
        "response": user_friendly,
        "error": None,
        "context": {**state.get("context", {}), "last_error": error},
    }


async def tools_node(state: AgentState) -> dict[str, Any]:
    """Execute tool calls from the last AI message asynchronously."""
    messages = list(state.get("messages", []))
    tool_map = {t.name: t for t in ALL_TOOLS}

    if not messages or not isinstance(messages[-1], AIMessage):
        return {"messages": messages}

    last_msg = messages[-1]
    new_messages = list(messages)

    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        for tool_call in last_msg.tool_calls:
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})
            tool_id = tool_call.get("id", "")

            if tool_name in tool_map:
                try:
                    result = await tool_map[tool_name].ainvoke(tool_args)
                    new_messages.append(
                        ToolMessage(content=str(result), tool_call_id=tool_id)
                    )
                except Exception as e:
                    logger.error("Tool execution error (%s): %s", tool_name, e)
                    new_messages.append(
                        ToolMessage(
                            content=f"Error executing {tool_name}: {e}",
                            tool_call_id=tool_id,
                        )
                    )
            else:
                new_messages.append(
                    ToolMessage(
                        content=f"Unknown tool: {tool_name}",
                        tool_call_id=tool_id,
                    )
                )

    return {"messages": new_messages}


NODE_MAP = {
    "router": router_node,
    "conversation_agent": conversation_node,
    "task_agent": task_node,
    "research_agent": research_node,
    "coding_agent": coding_node,
    "email_agent": email_node,
    "calendar_agent": calendar_node,
    "automation_agent": automation_node,
    "memory_agent": memory_node,
    "file_agent": file_node,
    "vision_agent": vision_node,
    "notes_agent": notes_node,
    "planner_agent": planner_node,
    "synthesis": synthesis_node,
    "error": error_node,
    "tools": tools_node,
}
