"""Base plugin class for JARVIS AI assistant."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    """Plugin information."""
    name: str
    version: str
    description: str
    author: str
    enabled: bool = True
    dependencies: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


class BasePlugin(ABC):
    """Abstract base class for all plugins."""

    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = {}
        self._config: Dict[str, Any] = {}
        self._logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description."""
        pass

    @property
    @abstractmethod
    def author(self) -> str:
        """Plugin author."""
        pass

    async def initialize(self) -> None:
        """Initialize the plugin."""
        self._logger.info(f"Initializing plugin: {self.name}")

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        self._logger.info(f"Shutting down plugin: {self.name}")

    @abstractmethod
    async def execute(self, action: str, **kwargs) -> Any:
        """Execute a plugin action."""
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Get list of plugin capabilities."""
        pass

    def get_info(self) -> PluginInfo:
        """Get plugin information."""
        return PluginInfo(
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
            enabled=True,
            config=self._config
        )

    def set_config(self, config: Dict[str, Any]) -> None:
        """Set plugin configuration."""
        self._config.update(config)

    def get_config(self) -> Dict[str, Any]:
        """Get plugin configuration."""
        return self._config.copy()

    def register_hook(self, event: str, callback: Callable) -> None:
        """Register a hook for an event."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    def unregister_hook(self, event: str, callback: Callable) -> None:
        """Unregister a hook."""
        if event in self._hooks:
            self._hooks[event] = [
                cb for cb in self._hooks[event] if cb != callback
            ]

    async def trigger_hook(self, event: str, **kwargs) -> List[Any]:
        """Trigger all hooks for an event."""
        results = []
        for callback in self._hooks.get(event, []):
            try:
                result = await callback(**kwargs) if callable(callback) else None
                results.append(result)
            except Exception as e:
                self._logger.error(f"Hook error in {self.name}.{event}: {e}")
        return results

    async def on_message(self, message: str, context: Optional[Dict] = None) -> Optional[str]:
        """Handle incoming message."""
        return None

    async def on_command(self, command: str, args: Optional[Dict] = None) -> Optional[str]:
        """Handle incoming command."""
        return None

    async def on_event(self, event: str, data: Optional[Dict] = None) -> None:
        """Handle an event."""
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} v{self.version}>"
