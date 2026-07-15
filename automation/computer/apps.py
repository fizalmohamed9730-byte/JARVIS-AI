"""Cross-platform application management for opening, closing, and searching apps."""

import logging
import os
import platform
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_SYSTEM = platform.system()


class ApplicationManager:
    """Manages launching, closing, and discovering desktop applications."""

    # Common application name aliases mapped to process / executable names
    _ALIASES: Dict[str, Dict[str, str]] = {
        "chrome": {
            "Windows": "chrome.exe",
            "Linux": "google-chrome",
            "Darwin": "Google Chrome",
        },
        "firefox": {
            "Windows": "firefox.exe",
            "Linux": "firefox",
            "Darwin": "Firefox",
        },
        "edge": {
            "Windows": "msedge.exe",
            "Linux": "microsoft-edge",
            "Darwin": "Microsoft Edge",
        },
        "notepad": {
            "Windows": "notepad.exe",
            "Linux": "notepadqq",
            "Darwin": "TextEdit",
        },
        "code": {
            "Windows": "Code.exe",
            "Linux": "code",
            "Darwin": "Visual Studio Code",
        },
        "vscode": {
            "Windows": "Code.exe",
            "Linux": "code",
            "Darwin": "Visual Studio Code",
        },
        "explorer": {
            "Windows": "explorer.exe",
            "Linux": "nautilus",
            "Darwin": "Finder",
        },
        "calculator": {
            "Windows": "calc.exe",
            "Linux": "gnome-calculator",
            "Darwin": "Calculator",
        },
        "spotify": {
            "Windows": "Spotify.exe",
            "Linux": "spotify",
            "Darwin": "Spotify",
        },
        "terminal": {
            "Windows": "cmd.exe",
            "Linux": "gnome-terminal",
            "Darwin": "Terminal",
        },
        "cmd": {
            "Windows": "cmd.exe",
            "Linux": "gnome-terminal",
            "Darwin": "Terminal",
        },
        "powershell": {
            "Windows": "powershell.exe",
            "Linux": "pwsh",
            "Darwin": "pwsh",
        },
    }

    def open_application(self, name: str) -> Dict[str, Any]:
        """Launch an application by name.

        Tries process-based lookup first, then falls back to OS-specific
        mechanisms (``start`` on Windows, ``open`` on macOS, ``xdg-open``
        / ``nohup`` on Linux).

        Args:
            name: Application name or executable path.

        Returns:
            Dictionary with ``success`` and optional ``pid`` or ``error``.
        """
        logger.info("Opening application: %s", name)
        normalized = name.lower().strip()

        if _SYSTEM == "Windows":
            return self._open_windows(normalized)
        elif _SYSTEM == "Darwin":
            return self._open_macos(normalized)
        else:
            return self._open_linux(normalized)

    def _open_windows(self, name: str) -> Dict[str, Any]:
        alias_info = self._ALIASES.get(name, {})
        exe = alias_info.get("Windows", name)

        # If already running, bring to front via PowerShell
        if self._is_running(exe):
            self._bring_to_front_windows(exe)
            return {"success": True, "message": f"{name} already running, brought to front"}

        try:
            # Try subprocess.Popen first for direct executable launch
            process = subprocess.Popen(
                [exe],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            return {"success": True, "pid": process.pid, "message": f"Launched {name}"}
        except FileNotFoundError:
            pass

        try:
            # Fallback: use `start` via cmd
            subprocess.Popen(
                ["cmd", "/c", "start", "", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return {"success": True, "message": f"Launched {name} via start command"}
        except Exception as exc:
            logger.exception("Failed to open %s on Windows", name)
            return {"success": False, "error": str(exc)}

    def _open_macos(self, name: str) -> Dict[str, Any]:
        alias_info = self._ALIASES.get(name, {})
        app_name = alias_info.get("Darwin", name)

        if self._is_running(app_name):
            return {"success": True, "message": f"{name} already running"}

        try:
            subprocess.Popen(
                ["open", "-a", app_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return {"success": True, "message": f"Launched {name}"}
        except Exception as exc:
            logger.exception("Failed to open %s on macOS", name)
            return {"success": False, "error": str(exc)}

    def _open_linux(self, name: str) -> Dict[str, Any]:
        alias_info = self._ALIASES.get(name, {})
        exe = alias_info.get("Linux", name)

        if self._is_running(exe):
            return {"success": True, "message": f"{name} already running"}

        try:
            subprocess.Popen(
                ["nohup", exe],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return {"success": True, "message": f"Launched {name}"}
        except FileNotFoundError:
            # Try xdg-open for .desktop files or URLs
            try:
                subprocess.Popen(
                    ["xdg-open", name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return {"success": True, "message": f"Launched {name} via xdg-open"}
            except Exception as exc:
                logger.exception("Failed to open %s on Linux", name)
                return {"success": False, "error": str(exc)}

    def close_application(self, name: str) -> Dict[str, Any]:
        """Close/kill an application by process name.

        Args:
            name: Application name or process name.

        Returns:
            Dictionary with ``success`` status.
        """
        logger.info("Closing application: %s", name)
        normalized = name.lower().strip()

        if _SYSTEM == "Windows":
            exe = self._ALIASES.get(normalized, {}).get("Windows", name)
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", exe],
                    capture_output=True,
                    timeout=10,
                )
                return {"success": True, "message": f"Closed {name}"}
            except Exception as exc:
                return {"success": False, "error": str(exc)}
        else:
            proc_name = self._ALIASES.get(normalized, {}).get(_SYSTEM, name)
            try:
                subprocess.run(
                    ["pkill", "-f", proc_name],
                    capture_output=True,
                    timeout=10,
                )
                return {"success": True, "message": f"Closed {name}"}
            except Exception as exc:
                return {"success": False, "error": str(exc)}

    def get_running_apps(self) -> List[Dict[str, str]]:
        """Return list of running applications with name and PID."""
        apps: List[Dict[str, str]] = []
        try:
            if _SYSTEM == "Windows":
                output = subprocess.check_output(
                    ["tasklist", "/FO", "CSV", "/NH"],
                    text=True,
                    timeout=15,
                )
                for line in output.strip().splitlines():
                    parts = line.strip('"').split('","')
                    if len(parts) >= 2:
                        apps.append({"name": parts[0], "pid": parts[1]})
            else:
                output = subprocess.check_output(
                    ["ps", "axo", "pid,comm"],
                    text=True,
                    timeout=15,
                )
                for line in output.strip().splitlines()[1:]:
                    parts = line.strip().split(None, 1)
                    if len(parts) >= 2:
                        apps.append({"name": parts[1], "pid": parts[0]})
        except Exception as exc:
            logger.exception("Failed to list running apps")
        return apps

    def search_applications(self, query: str) -> List[str]:
        """Search for installed applications matching *query*."""
        results: List[str] = []
        query_lower = query.lower()

        if _SYSTEM == "Windows":
            results = self._search_windows(query_lower)
        elif _SYSTEM == "Darwin":
            results = self._search_macos(query_lower)
        else:
            results = self._search_linux(query_lower)

        return results

    def _search_windows(self, query: str) -> List[str]:
        """Search Windows Start Menu and registry for applications."""
        results: List[str] = []
        start_menu = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs")
        public_start = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"

        for search_dir in [start_menu, public_start]:
            if not os.path.isdir(search_dir):
                continue
            for root, _dirs, files in os.walk(search_dir):
                for f in files:
                    if f.lower().endswith((".lnk", ".exe")) and query in f.lower():
                        results.append(os.path.join(root, f))

        # Also search PATH
        for path_dir in os.environ.get("PATH", "").split(os.pathsep):
            if not os.path.isdir(path_dir):
                continue
            try:
                for f in os.listdir(path_dir):
                    if query in f.lower() and f.lower().endswith(".exe"):
                        results.append(os.path.join(path_dir, f))
            except PermissionError:
                continue

        return results[:20]

    def _search_macos(self, query: str) -> List[str]:
        """Use Spotlight (mdfind) to search for applications on macOS."""
        try:
            output = subprocess.check_output(
                ["mdfind", "kMDItemKind == 'Application'", "-name", query],
                text=True,
                timeout=10,
            )
            return [line.strip() for line in output.strip().splitlines() if line.strip()][:20]
        except Exception:
            return []

    def _search_linux(self, query: str) -> List[str]:
        """Search .desktop files on Linux for matching applications."""
        results: List[str] = []
        xdg_data = os.environ.get("XDG_DATA_DIRS", "/usr/share:/usr/local/share")
        for data_dir in xdg_data.split(":"):
            apps_dir = os.path.join(data_dir, "applications")
            if not os.path.isdir(apps_dir):
                continue
            for f in os.listdir(apps_dir):
                if f.endswith(".desktop") and query in f.lower():
                    results.append(f.replace(".desktop", ""))
        return results[:20]

    def _is_running(self, name: str) -> bool:
        """Check if an application with the given process name is running."""
        try:
            if _SYSTEM == "Windows":
                output = subprocess.check_output(
                    ["tasklist", "/FI", f"IMAGENAME eq {name}"],
                    text=True,
                    timeout=10,
                )
                return name.lower() in output.lower()
            else:
                output = subprocess.check_output(
                    ["pgrep", "-f", name],
                    text=True,
                    timeout=10,
                )
                return bool(output.strip())
        except Exception:
            return False

    def _bring_to_front_windows(self, exe_name: str) -> None:
        """Attempt to bring an already-running Windows application to the foreground."""
        try:
            import ctypes
            user32 = ctypes.windll.user32

            def enum_callback(hwnd, _):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buf, length + 1)
                        # Simple heuristic – match title substring
                        if exe_name.replace(".exe", "").lower() in buf.value.lower():
                            user32.SetForegroundWindow(hwnd)
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
            user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
        except Exception:
            logger.debug("Could not bring %s to front", exe_name)
