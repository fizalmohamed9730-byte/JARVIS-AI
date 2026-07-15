"""
JARVIS Memory System
====================

Multi-layered memory architecture including short-term conversation memory,
long-term semantic memory, vector storage, and user profiling.

Usage:
    from memory import MemoryManager

    manager = MemoryManager()
    await manager.add_memory("User prefers dark mode", category="preferences")
    results = await manager.search_memory("display settings")
"""

from memory.manager import MemoryManager
from memory.long_term_memory import LongTermMemory
from memory.user_profile import UserProfile

__all__ = ["MemoryManager", "LongTermMemory", "UserProfile"]
__version__ = "1.0.0"
