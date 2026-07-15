"""JARVIS AI agent tools package."""

from __future__ import annotations

from typing import Sequence

from langchain_core.tools import BaseTool

from agents.tools.web_tools import web_tools
from agents.tools.file_tools import file_tools
from agents.tools.system_tools import system_tools
from agents.tools.email_tools import email_tools
from agents.tools.calendar_tools import calendar_tools
from agents.tools.memory_tools import memory_tools
from agents.tools.task_tools import task_tools
from agents.tools.vision_tools import vision_tools
from agents.tools.notes_tools import notes_tools
from agents.tools.utility_tools import utility_tools
from agents.tools.planner import planner_tools

ALL_TOOLS: list[BaseTool] = [
    *web_tools,
    *file_tools,
    *system_tools,
    *email_tools,
    *calendar_tools,
    *memory_tools,
    *task_tools,
    *vision_tools,
    *notes_tools,
    *utility_tools,
    *planner_tools,
]

CONVERSATION_TOOLS: list[BaseTool] = [*utility_tools, *memory_tools]
TASK_TOOLS: list[BaseTool] = [*task_tools, *planner_tools]
RESEARCH_TOOLS: list[BaseTool] = [*web_tools, *utility_tools]
CODING_TOOLS: list[BaseTool] = [*file_tools, *web_tools]
EMAIL_TOOLS: list[BaseTool] = email_tools
CALENDAR_TOOLS: list[BaseTool] = calendar_tools
AUTOMATION_TOOLS: list[BaseTool] = system_tools
FILE_TOOLS: list[BaseTool] = file_tools
MEMORY_TOOLS: list[BaseTool] = memory_tools
VISION_TOOLS: list[BaseTool] = vision_tools
NOTES_TOOLS: list[BaseTool] = notes_tools
PLANNER_TOOLS: list[BaseTool] = planner_tools

__all__ = [
    "ALL_TOOLS",
    "CONVERSATION_TOOLS",
    "TASK_TOOLS",
    "RESEARCH_TOOLS",
    "CODING_TOOLS",
    "EMAIL_TOOLS",
    "CALENDAR_TOOLS",
    "AUTOMATION_TOOLS",
    "FILE_TOOLS",
    "MEMORY_TOOLS",
    "VISION_TOOLS",
    "NOTES_TOOLS",
    "PLANNER_TOOLS",
    "web_tools",
    "file_tools",
    "system_tools",
    "email_tools",
    "calendar_tools",
    "memory_tools",
    "task_tools",
    "vision_tools",
    "notes_tools",
    "utility_tools",
    "planner_tools",
]
