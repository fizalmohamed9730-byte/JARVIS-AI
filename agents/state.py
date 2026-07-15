"""LangGraph state definitions for JARVIS AI agent system."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class Intent(str, Enum):
    """Classified user intent categories."""

    CONVERSATION = "conversation"
    TASK = "task"
    RESEARCH = "research"
    CODING = "coding"
    EMAIL = "email"
    CALENDAR = "calendar"
    AUTOMATION = "automation"
    FILE = "file"
    MEMORY = "memory"
    VISION = "vision"
    NOTES = "notes"
    PLANNING = "planning"
    GENERAL = "general"


class AgentState(TypedDict, total=False):
    """Primary state passed through the main graph."""

    messages: list[BaseMessage]
    user_input: str
    context: dict[str, Any]
    memory: dict[str, Any]
    tools_output: dict[str, Any]
    next_action: str
    intent: str
    error: Optional[str]
    response: Optional[str]
    conversation_id: str
    user_id: str
    timestamp: str
    metadata: dict[str, Any]


class ConversationState(TypedDict, total=False):
    """State for the conversation agent."""

    messages: list[BaseMessage]
    user_input: str
    memory_context: dict[str, Any]
    personality: str
    response: Optional[str]
    context: dict[str, Any]


class TaskState(TypedDict, total=False):
    """State for the task management agent."""

    messages: list[BaseMessage]
    user_input: str
    tasks: list[dict[str, Any]]
    action: str
    task_id: Optional[str]
    task_data: Optional[dict[str, Any]]
    response: Optional[str]
    context: dict[str, Any]


class ResearchState(TypedDict, total=False):
    """State for the research agent."""

    messages: list[BaseMessage]
    query: str
    search_results: list[dict[str, Any]]
    synthesized_info: Optional[str]
    sources: list[str]
    response: Optional[str]
    context: dict[str, Any]


class CodingState(TypedDict, total=False):
    """State for the coding agent."""

    messages: list[BaseMessage]
    user_input: str
    language: Optional[str]
    code: Optional[str]
    explanation: Optional[str]
    error_output: Optional[str]
    response: Optional[str]
    context: dict[str, Any]


class EmailState(TypedDict, total=False):
    """State for the email agent."""

    messages: list[BaseMessage]
    user_input: str
    action: str
    emails: list[dict[str, Any]]
    draft: Optional[dict[str, Any]]
    response: Optional[str]
    context: dict[str, Any]


class CalendarState(TypedDict, total=False):
    """State for the calendar agent."""

    messages: list[BaseMessage]
    user_input: str
    action: str
    events: list[dict[str, Any]]
    event_data: Optional[dict[str, Any]]
    response: Optional[str]
    context: dict[str, Any]


class AutomationState(TypedDict, total=False):
    """State for the system automation agent."""

    messages: list[BaseMessage]
    user_input: str
    command: str
    command_result: Optional[dict[str, Any]]
    response: Optional[str]
    context: dict[str, Any]


class FileState(TypedDict, total=False):
    """State for the file operations agent."""

    messages: list[BaseMessage]
    user_input: str
    action: str
    file_path: Optional[str]
    file_content: Optional[str]
    search_results: list[dict[str, Any]]
    response: Optional[str]
    context: dict[str, Any]


class MemoryState(TypedDict, total=False):
    """State for the memory agent."""

    messages: list[BaseMessage]
    user_input: str
    action: str
    memories: list[dict[str, Any]]
    query: Optional[str]
    response: Optional[str]
    context: dict[str, Any]


class NotesState(TypedDict, total=False):
    """State for the notes agent."""

    messages: list[BaseMessage]
    user_input: str
    action: str
    notes: list[dict[str, Any]]
    note_data: Optional[dict[str, Any]]
    response: Optional[str]
    context: dict[str, Any]


class VisionState(TypedDict, total=False):
    """State for the vision agent."""

    messages: list[BaseMessage]
    image_path: Optional[str]
    analysis: Optional[str]
    ocr_text: Optional[str]
    response: Optional[str]
    context: dict[str, Any]


class PlannerState(TypedDict, total=False):
    """State for the planning agent."""

    messages: list[BaseMessage]
    user_input: str
    goal: str
    plan: Optional[dict[str, Any]]
    current_step: Optional[int]
    response: Optional[str]
    context: dict[str, Any]


class RouterOutput(TypedDict):
    """Output of the router node."""

    intent: str
    confidence: float
    sub_intent: Optional[str]
    parameters: dict[str, Any]


class ToolCallResult(TypedDict):
    """Standardized tool call result."""

    tool_name: str
    success: bool
    result: Any
    error: Optional[str]
    metadata: dict[str, Any]


def create_initial_state(
    user_input: str,
    user_id: str = "default",
    conversation_id: str = "",
) -> AgentState:
    """Create an initial AgentState from user input."""
    return AgentState(
        messages=[],
        user_input=user_input,
        context={},
        memory={},
        tools_output={},
        next_action="",
        intent="",
        error=None,
        response=None,
        conversation_id=conversation_id or f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        user_id=user_id,
        timestamp=datetime.now().isoformat(),
        metadata={},
    )
