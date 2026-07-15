"""Plugin manager for JARVIS AI assistant."""

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Type
from dataclasses import dataclass, field

from .base import BasePlugin, PluginInfo

logger = logging.getLogger(__name__)


@dataclass
class PluginState:
    """State of a loaded plugin."""
    name: str
    instance: BasePlugin
    enabled: bool = True
    loaded: bool = False
    error: Optional[str] = None


class PluginManager:
    """Manages plugin lifecycle and discovery."""

    def __init__(self, plugins_dir: Optional[str] = None):
        self.plugins_dir = Path(plugins_dir or "plugins/builtin")
        self._plugins: Dict[str, PluginState] = {}
        self._plugin_classes: Dict[str, Type[BasePlugin]] = {}
        self._config: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the plugin manager."""
        if self._initialized:
            return

        logger.info("Initializing plugin manager...")
        self.discover_plugins()
        self._initialized = True
        logger.info(f"Plugin manager initialized with {len(self._plugin_classes)} plugins")

    def discover_plugins(self) -> List[str]:
        """Discover available plugins."""
        discovered = []

        if self.plugins_dir.exists():
            for item in self.plugins_dir.iterdir():
                if item.suffix == ".py" and not item.name.startswith("_"):
                    try:
                        plugin_name = item.stem
                        spec = importlib.util.spec_from_file_location(
                            f"plugins.builtin.{plugin_name}",
                            str(item)
                        )
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[spec.name] = module
                            spec.loader.exec_module(module)

                            for attr_name in dir(module):
                                attr = getattr(module, attr_name)
                                if (
                                    isinstance(attr, type)
                                    and issubclass(attr, BasePlugin)
                                    and attr is not BasePlugin
                                ):
                                    self._plugin_classes[plugin_name] = attr
                                    discovered.append(plugin_name)
                                    logger.debug(f"Discovered plugin: {plugin_name}")
                    except Exception as e:
                        logger.error(f"Failed to discover plugin {item.name}: {e}")

        return discovered

    async def load_plugin(self, name: str) -> Optional[BasePlugin]:
        """Load a plugin by name."""
        if name in self._plugins:
            if self._plugins[name].instance:
                return self._plugins[name].instance

        plugin_class = self._plugin_classes.get(name)
        if not plugin_class:
            logger.error(f"Plugin not found: {name}")
            return None

        try:
            instance = plugin_class()
            config = self._config.get(name, {})
            instance.set_config(config)

            await instance.initialize()

            self._plugins[name] = PluginState(
                name=name,
                instance=instance,
                enabled=True,
                loaded=True
            )

            logger.info(f"Loaded plugin: {name}")
            return instance

        except Exception as e:
            logger.error(f"Failed to load plugin {name}: {e}")
            self._plugins[name] = PluginState(
                name=name,
                instance=None,
                enabled=False,
                loaded=False,
                error=str(e)
            )
            return None

    async def unload_plugin(self, name: str) -> bool:
        """Unload a plugin."""
        state = self._plugins.get(name)
        if not state or not state.instance:
            return False

        try:
            await state.instance.shutdown()
            del self._plugins[name]
            logger.info(f"Unloaded plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to unload plugin {name}: {e}")
            return False

    async def enable_plugin(self, name: str) -> bool:
        """Enable a plugin."""
        state = self._plugins.get(name)
        if state:
            state.enabled = True
            if not state.loaded and state.instance:
                await state.instance.initialize()
                state.loaded = True
            return True

        instance = await self.load_plugin(name)
        return instance is not None

    async def disable_plugin(self, name: str) -> bool:
        """Disable a plugin."""
        state = self._plugins.get(name)
        if state:
            state.enabled = False
            if state.loaded and state.instance:
                await state.instance.shutdown()
                state.loaded = False
            return True
        return False

    def get_plugin_config(self, name: str) -> Dict[str, Any]:
        """Get plugin configuration."""
        return self._config.get(name, {})

    def update_plugin_config(self, name: str, config: Dict[str, Any]) -> bool:
        """Update plugin configuration."""
        self._config[name] = config

        state = self._plugins.get(name)
        if state and state.instance:
            state.instance.set_config(config)
            return True
        return True

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """Get a loaded plugin instance."""
        state = self._plugins.get(name)
        if state and state.loaded:
            return state.instance
        return None

    def get_all_plugins(self) -> Dict[str, PluginInfo]:
        """Get information about all plugins."""
        plugins = {}

        for name, plugin_class in self._plugin_classes.items():
            state = self._plugins.get(name)
            if state and state.instance:
                plugins[name] = state.instance.get_info()
            else:
                try:
                    instance = plugin_class()
                    plugins[name] = instance.get_info()
                except Exception:
                    plugins[name] = PluginInfo(
                        name=name,
                        version="unknown",
                        description="Failed to load",
                        author="unknown"
                    )

        return plugins

    def get_loaded_plugins(self) -> List[str]:
        """Get list of loaded plugin names."""
        return [
            name for name, state in self._plugins.items()
            if state.loaded
        ]

    def get_enabled_plugins(self) -> List[str]:
        """Get list of enabled plugin names."""
        return [
            name for name, state in self._plugins.items()
            if state.enabled
        ]

    async def execute_plugin_action(
        self,
        plugin_name: str,
        action: str,
        **kwargs
    ) -> Any:
        """Execute an action on a plugin."""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            raise ValueError(f"Plugin not loaded: {plugin_name}")

        return await plugin.execute(action, **kwargs)

    async def trigger_event(
        self,
        event: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Trigger an event on all enabled plugins."""
        results = {}

        for name, state in self._plugins.items():
            if state.enabled and state.loaded and state.instance:
                try:
                    if event == "message":
                        result = await state.instance.on_message(
                            kwargs.get("message", ""),
                            kwargs.get("context")
                        )
                    elif event == "command":
                        result = await state.instance.on_command(
                            kwargs.get("command", ""),
                            kwargs.get("args")
                        )
                    else:
                        result = await state.instance.on_event(event, kwargs)

                    if result is not None:
                        results[name] = result
                except Exception as e:
                    logger.error(f"Event trigger error in {name}: {e}")

        return results

    async def shutdown(self) -> None:
        """Shutdown all plugins."""
        for name, state in self._plugins.items():
            if state.loaded and state.instance:
                try:
                    await state.instance.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down {name}: {e}")

        self._plugins.clear()
        self._initialized = False
        logger.info("Plugin manager shut down")
