"""Plugin system for JARVIS AI assistant."""

from .manager import PluginManager
from .base import BasePlugin

__all__ = ["PluginManager", "BasePlugin"]
