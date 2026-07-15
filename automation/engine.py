"""Central automation engine coordinating all JARVIS automation subsystems."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from automation.computer import ComputerManager
from automation.browser import BrowserManager
from automation.files import FileManager, DocumentGenerator

logger = logging.getLogger(__name__)


class AutomationAction:
    """Represents a single recorded automation action for rollback support."""

    def __init__(
        self,
        action_id: str,
        command_type: str,
        params: Dict[str, Any],
        result: Any,
        timestamp: datetime,
        rollback_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.action_id = action_id
        self.command_type = command_type
        self.params = params
        self.result = result
        self.timestamp = timestamp
        self.rollback_data = rollback_data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "command_type": self.command_type,
            "params": self.params,
            "result": self.result,
            "timestamp": self.timestamp.isoformat(),
            "rollback_data": self.rollback_data,
        }


class SafetyCheck:
    """Defines safety constraints for dangerous operations."""

    DANGEROUS_COMMANDS = frozenset(
        {
            "system.shutdown",
            "system.restart",
            "system.sleep",
            "file.delete",
            "file.move",
            "browser.download",
        }
    )

    DESTRUCTIVE_COMMANDS = frozenset(
        {
            "system.shutdown",
            "system.restart",
            "file.delete",
        }
    )

    @classmethod
    def is_dangerous(cls, command_type: str) -> bool:
        return command_type in cls.DANGEROUS_COMMANDS

    @classmethod
    def is_destructive(cls, command_type: str) -> bool:
        return command_type in cls.DESTRUCTIVE_COMMANDS

    @classmethod
    def requires_confirmation(cls, command_type: str) -> bool:
        return cls.is_dangerous(command_type)


class AutomationEngine:
    """Central automation engine that routes commands to appropriate subsystems.

    Provides a unified interface for executing computer, browser, and file
    automation commands with safety checks, logging, and rollback support.
    """

    def __init__(self) -> None:
        self._computer = ComputerManager()
        self._browser = BrowserManager()
        self._files = FileManager()
        self._doc_generator = DocumentGenerator()
        self._action_history: List[AutomationAction] = []
        self._command_registry: Dict[str, Callable] = {}
        self._pending_confirmations: Dict[str, AutomationAction] = {}
        self._register_commands()
        logger.info("AutomationEngine initialized with %d registered commands", len(self._command_registry))

    def _register_commands(self) -> None:
        """Map command_type strings to handler callables."""
        self._command_registry = {
            # Computer commands
            "computer.open_app": self._computer.open_application,
            "computer.close_app": self._computer.close_application,
            "computer.get_apps": self._computer.get_running_apps,
            "computer.search_apps": self._computer.search_applications,
            "computer.get_volume": self._computer.get_volume,
            "computer.set_volume": self._computer.set_volume,
            "computer.get_brightness": self._computer.get_brightness,
            "computer.set_brightness": self._computer.set_brightness,
            "computer.get_wifi": self._computer.get_wifi_status,
            "computer.toggle_wifi": self._computer.toggle_wifi,
            "computer.get_bluetooth": self._computer.get_bluetooth_status,
            "computer.toggle_bluetooth": self._computer.toggle_bluetooth,
            "computer.battery": self._computer.get_battery_info,
            "computer.system_info": self._computer.get_system_info,
            "computer.shutdown": self._computer.shutdown,
            "computer.restart": self._computer.restart,
            "computer.sleep": self._computer.sleep,
            "computer.lock": self._computer.lock_screen,
            "computer.get_clipboard": self._computer.get_clipboard,
            "computer.set_clipboard": self._computer.set_clipboard,
            "computer.screenshot": self._computer.take_screenshot,
            # Browser commands
            "browser.open_url": self._browser.open_url,
            "browser.search_google": self._browser.search_google,
            "browser.search_youtube": self._browser.search_youtube,
            "browser.read_page": self._browser.read_page_content,
            "browser.fill_form": self._browser.fill_form,
            "browser.click": self._browser.click_element,
            "browser.download": self._browser.download_file,
            "browser.get_history": self._browser.get_history,
            # File commands
            "file.search": self._files.search_files,
            "file.read": self._files.read_file,
            "file.create": self._files.create_file,
            "file.write": self._files.write_file,
            "file.move": self._files.move_file,
            "file.copy": self._files.copy_file,
            "file.delete": self._files.delete_file,
            "file.info": self._files.get_file_info,
            "file.batch_rename": self._files.batch_rename,
            "file.organize": self._files.organize_folder,
            "file.recent": self._files.get_recent_files,
            # Document generation
            "doc.word": self._doc_generator.generate_word,
            "doc.excel": self._doc_generator.generate_excel,
            "doc.presentation": self._doc_generator.generate_presentation,
            "doc.pdf": self._doc_generator.generate_pdf,
            "doc.csv": self._doc_generator.generate_csv,
        }

    def get_capabilities(self) -> List[str]:
        """Return sorted list of all available automation command types."""
        return sorted(self._command_registry.keys())

    def execute_command(
        self,
        command_type: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        skip_safety: bool = False,
    ) -> Dict[str, Any]:
        """Execute an automation command with safety checks and logging.

        Args:
            command_type: Registered command identifier (e.g. ``computer.set_volume``).
            params: Keyword arguments forwarded to the handler.
            skip_safety: If *True*, bypass confirmation prompts (use with caution).

        Returns:
            Dictionary containing ``success``, ``result``, ``action_id``, and
            ``timestamp`` keys.
        """
        params = params or {}
        action_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        logger.info(
            "Executing command %s (id=%s) params=%s",
            command_type,
            action_id,
            {k: v for k, v in params.items() if k != "password"},
        )

        if command_type not in self._command_registry:
            error_msg = f"Unknown command type: {command_type}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "action_id": action_id}

        if not skip_safety and SafetyCheck.requires_confirmation(command_type):
            confirmation_id = str(uuid.uuid4())
            action = AutomationAction(
                action_id=action_id,
                command_type=command_type,
                params=params,
                result=None,
                timestamp=timestamp,
            )
            self._pending_confirmations[confirmation_id] = action
            logger.warning(
                "Command %s requires confirmation (confirmation_id=%s)",
                command_type,
                confirmation_id,
            )
            return {
                "success": False,
                "requires_confirmation": True,
                "confirmation_id": confirmation_id,
                "message": f"Dangerous operation '{command_type}' requires user confirmation.",
                "action_id": action_id,
            }

        return self._execute_and_record(command_type, params, action_id, timestamp)

    def confirm_action(self, confirmation_id: str) -> Dict[str, Any]:
        """Execute a previously pending dangerous action after user confirmation."""
        if confirmation_id not in self._pending_confirmations:
            return {"success": False, "error": "Invalid or expired confirmation id"}

        action = self._pending_confirmations.pop(confirmation_id)
        logger.info("Confirmed action %s for command %s", action.action_id, action.command_type)
        return self._execute_and_record(
            action.command_type,
            action.params,
            action.action_id,
            action.timestamp,
        )

    def cancel_action(self, confirmation_id: str) -> bool:
        """Cancel a pending confirmation."""
        if confirmation_id in self._pending_confirmations:
            action = self._pending_confirmations.pop(confirmation_id)
            logger.info("Cancelled pending action %s", confirmation_id)
            return True
        return False

    def _execute_and_record(
        self,
        command_type: str,
        params: Dict[str, Any],
        action_id: str,
        timestamp: datetime,
    ) -> Dict[str, Any]:
        import asyncio
        import inspect

        handler = self._command_registry[command_type]
        try:
            rollback_data = self._capture_rollback_data(command_type, params)

            if inspect.iscoroutinefunction(handler):
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        result = pool.submit(
                            lambda: asyncio.run(handler(**params) if params else handler())
                        ).result(timeout=30)
                else:
                    result = asyncio.run(handler(**params) if params else handler())
            else:
                result = handler(**params) if params else handler()

            action = AutomationAction(
                action_id=action_id,
                command_type=command_type,
                params=params,
                result=result,
                timestamp=timestamp,
                rollback_data=rollback_data,
            )
            self._action_history.append(action)

            logger.info("Command %s succeeded (id=%s)", command_type, action_id)
            return {
                "success": True,
                "result": result,
                "action_id": action_id,
                "timestamp": timestamp.isoformat(),
            }
        except Exception as exc:
            logger.exception("Command %s failed (id=%s)", command_type, action_id)
            action = AutomationAction(
                action_id=action_id,
                command_type=command_type,
                params=params,
                result=None,
                timestamp=timestamp,
            )
            self._action_history.append(action)
            return {
                "success": False,
                "error": str(exc),
                "action_id": action_id,
                "timestamp": timestamp.isoformat(),
            }

    def _capture_rollback_data(
        self, command_type: str, params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Capture state needed to undo a command where possible."""
        try:
            if command_type == "file.move":
                return {"reverse_move": True, "source": params.get("dest"), "dest": params.get("source")}
            if command_type == "file.write":
                path = params.get("path", "")
                try:
                    existing = self._files.read_file(path=path)
                    return {"restore_content": existing}
                except Exception:
                    return {"restore_content": None}
            if command_type == "computer.set_volume":
                return {"previous_volume": self._computer.get_volume()}
            if command_type == "computer.set_brightness":
                return {"previous_brightness": self._computer.get_brightness()}
        except Exception:
            logger.debug("Could not capture rollback data for %s", command_type)
        return None

    def rollback(self, action_id: str) -> Dict[str, Any]:
        """Attempt to undo a previously executed action.

        Returns:
            Dictionary with ``success`` and optional ``result`` or ``error``.
        """
        action = None
        for a in self._action_history:
            if a.action_id == action_id:
                action = a
                break

        if action is None:
            return {"success": False, "error": f"Action {action_id} not found in history"}

        if action.rollback_data is None:
            return {"success": False, "error": "No rollback data available for this action"}

        rollback_id = str(uuid.uuid4())
        rollback_timestamp = datetime.now(timezone.utc)
        logger.info("Rolling back action %s (command=%s)", action_id, action.command_type)

        try:
            if action.command_type == "file.move":
                result = self._files.move_file(
                    source=action.rollback_data["source"],
                    dest=action.rollback_data["dest"],
                )
            elif action.command_type == "file.write":
                content = action.rollback_data.get("restore_content")
                if content is None:
                    return {"success": False, "error": "Original content not available"}
                result = self._files.write_file(path=action.params.get("path", ""), content=content)
            elif action.command_type == "computer.set_volume":
                prev = action.rollback_data["previous_volume"]
                result = self._computer.set_volume(level=prev)
            elif action.command_type == "computer.set_brightness":
                prev = action.rollback_data["previous_brightness"]
                result = self._computer.set_brightness(level=prev)
            else:
                return {"success": False, "error": f"Rollback not implemented for {action.command_type}"}

            rollback_action = AutomationAction(
                action_id=rollback_id,
                command_type=f"rollback.{action.command_type}",
                params=action.rollback_data,
                result=result,
                timestamp=rollback_timestamp,
            )
            self._action_history.append(rollback_action)
            return {"success": True, "result": result, "rollback_action_id": rollback_id}
        except Exception as exc:
            logger.exception("Rollback failed for action %s", action_id)
            return {"success": False, "error": str(exc)}

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the most recent automation actions."""
        recent = self._action_history[-limit:]
        return [a.to_dict() for a in reversed(recent)]

    async def initialize_browser(self, headless: bool = True) -> None:
        """Initialize the browser subsystem for browser automation commands."""
        await self._browser.initialize(headless=headless)

    async def close_browser(self) -> None:
        """Shut down the browser subsystem."""
        await self._browser.close()
