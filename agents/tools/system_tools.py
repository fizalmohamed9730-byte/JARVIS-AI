"""System automation tools for JARVIS AI agent system."""

from __future__ import annotations

import ctypes
import logging
import os
import platform
import subprocess
from typing import Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_WIN = platform.system() == "Windows"
_LINUX = platform.system() == "Linux"
_MAC = platform.system() == "Darwin"

_BLOCKED_COMMANDS = {
    "format", "rd", "rmdir", "del", "rm", "mkfs",
    "shutdown", "reboot", "halt", "poweroff",
    "reg delete", "regedit",
    "cipher /w",
    "icacls",
}


def _is_command_safe(command: str) -> bool:
    """Check if a command is safe to execute."""
    cmd_lower = command.lower().strip()
    for blocked in _BLOCKED_COMMANDS:
        if cmd_lower.startswith(blocked):
            return False
    dangerous_chars = {"|", "&", ";", "&&", "||", "$(", "`"}
    for char in dangerous_chars:
        if char in cmd_lower:
            return False
    return True


@tool
def open_application(name: str) -> str:
    """Open a desktop application by name.

    Args:
        name: Name of the application to open (e.g., 'notepad', 'chrome', 'calculator').

    Returns:
        A success or error message.
    """
    if not name or not name.strip():
        return "Error: Application name cannot be empty."

    name = name.strip()

    common_apps = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "cmd": "cmd.exe",
        "command prompt": "cmd.exe",
        "powershell": "powershell.exe",
        "task manager": "taskmgr.exe",
        "chrome": "chrome",
        "google chrome": "chrome",
        "firefox": "firefox",
        "edge": "msedge",
        "word": "winword",
        "excel": "excel",
        "powerpoint": "powerpnt",
        "visual studio code": "code",
        "vscode": "code",
        "code": "code",
        "spotify": "spotify",
        "discord": "discord",
        "slack": "slack",
        "teams": "teams",
        "zoom": "zoom",
    }

    app_cmd = common_apps.get(name.lower(), name)

    try:
        if _WIN:
            os.startfile(app_cmd)
        elif _MAC:
            subprocess.Popen(["open", "-a", app_cmd])
        else:
            subprocess.Popen([app_cmd])

        return f"Opened application: {name}"

    except FileNotFoundError:
        try:
            if _WIN:
                subprocess.Popen(["cmd", "/c", "start", "", app_cmd], shell=False)
                return f"Attempted to open: {name}"
        except Exception:
            pass
        return f"Error: Application '{name}' not found. Make sure it's installed and in PATH."
    except Exception as e:
        return f"Error opening {name}: {e}"


@tool
def close_application(name: str) -> str:
    """Close a running application by name.

    Args:
        name: Name of the application to close.

    Returns:
        A success or error message.
    """
    if not name or not name.strip():
        return "Error: Application name cannot be empty."

    name = name.strip()

    process_names = {
        "chrome": "chrome",
        "firefox": "firefox",
        "edge": "msedge",
        "notepad": "notepad",
        "code": "Code",
        "spotify": "Spotify",
        "discord": "Discord",
        "slack": "Slack",
        "teams": "Teams",
        "zoom": "Zoom",
    }

    process_name = process_names.get(name.lower(), name)

    try:
        if _WIN:
            result = subprocess.run(
                ["taskkill", "/IM", f"{process_name}.exe", "/F"],
                capture_output=True, text=True, timeout=10,
            )
        elif _MAC:
            result = subprocess.run(
                ["pkill", "-f", process_name],
                capture_output=True, text=True, timeout=10,
            )
        else:
            result = subprocess.run(
                ["pkill", "-f", process_name],
                capture_output=True, text=True, timeout=10,
            )

        if result.returncode == 0:
            return f"Closed application: {name}"
        else:
            return f"Application '{name}' may not be running or could not be closed."

    except Exception as e:
        return f"Error closing {name}: {e}"


@tool
def control_volume(action: str = "toggle", level: Optional[int] = None) -> str:
    """Control system volume.

    Args:
        action: Volume action - 'up', 'down', 'mute', 'unmute', 'toggle', 'set'.
        level: Volume level (0-100) when action is 'set'. Defaults to None.

    Returns:
        A description of the volume change performed.
    """
    action = (action or "toggle").lower().strip()

    try:
        if _WIN:
            return _volume_windows(action, level)
        elif _MAC:
            return _volume_mac(action, level)
        else:
            return _volume_linux(action, level)
    except Exception as e:
        return f"Error controlling volume: {e}"


def _volume_windows(action: str, level: Optional[int]) -> str:
    """Windows volume control using nircmd or PowerShell."""
    if action == "set" and level is not None:
        level = max(0, min(100, level))
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            return f"Volume set to {level}%"
        except ImportError:
            return f"Volume control requires pycaw. Install: pip install pycaw"

    if action == "up":
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
            current = volume.GetMasterVolumeLevelScalar()
            new_level = min(1.0, current + 0.05)
            volume.SetMasterVolumeLevelScalar(new_level, None)
            return f"Volume increased to {int(new_level * 100)}%"
        except ImportError:
            return "Volume control requires pycaw. Install: pip install pycaw"

    if action == "down":
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
            current = volume.GetMasterVolumeLevelScalar()
            new_level = max(0.0, current - 0.05)
            volume.SetMasterVolumeLevelScalar(new_level, None)
            return f"Volume decreased to {int(new_level * 100)}%"
        except ImportError:
            return "Volume control requires pycaw. Install: pip install pycaw"

    if action in ("mute", "toggle", "unmute"):
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
            muted = volume.GetMute()
            volume.SetMute(int(not muted) if action == "toggle" else (1 if action == "mute" else 0), None)
            state = "muted" if (action == "mute" or (action == "toggle" and muted)) else "unmuted"
            return f"Volume {state}"
        except ImportError:
            return "Volume control requires pycaw. Install: pip install pycaw"

    return f"Unknown volume action: {action}. Use 'up', 'down', 'mute', 'unmute', 'toggle', or 'set'."


def _volume_mac(action: str, level: Optional[int]) -> str:
    """macOS volume control."""
    if action == "set" and level is not None:
        level = max(0, min(100, level))
        scaled = level * 7 // 100
        subprocess.run(["osascript", "-e", f"set volume output volume {scaled}"])
        return f"Volume set to {level}%"

    if action == "up":
        subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) + 10)"])
        return "Volume increased"
    if action == "down":
        subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) - 10)"])
        return "Volume decreased"
    if action in ("mute", "toggle"):
        subprocess.run(["osascript", "-e", "set volume output muted (not output muted of (get volume settings))"])
        return "Volume toggled"

    return f"Unknown action: {action}"


def _volume_linux(action: str, level: Optional[int]) -> str:
    """Linux volume control using amixer."""
    if action == "set" and level is not None:
        level = max(0, min(100, level))
        subprocess.run(["amixer", "set", "Master", f"{level}%"])
        return f"Volume set to {level}%"
    if action == "up":
        subprocess.run(["amixer", "set", "Master", "5%+"])
        return "Volume increased"
    if action == "down":
        subprocess.run(["amixer", "set", "Master", "5%-"])
        return "Volume decreased"
    if action in ("mute", "toggle"):
        subprocess.run(["amixer", "set", "Master", "toggle"])
        return "Volume toggled"

    return f"Unknown action: {action}"


@tool
def control_brightness(level: int = -1) -> str:
    """Control screen brightness.

    Args:
        level: Brightness level (0-100). Pass -1 to query current brightness.

    Returns:
        Current or updated brightness level.
    """
    try:
        if _WIN:
            return _brightness_windows(level)
        elif _MAC:
            return _brightness_mac(level)
        else:
            return _brightness_linux(level)
    except Exception as e:
        return f"Error controlling brightness: {e}"


def _brightness_windows(level: int) -> str:
    """Windows brightness control."""
    if level < 0:
        return "Querying brightness is not fully supported on Windows without WMI."

    level = max(0, min(100, level))
    try:
        import wmi
        c = wmi.WMI(namespace="wmi")
        methods = c.WmiMonitorBrightnessMethods()
        if methods:
            methods[0].WmiSetBrightness(level, 0)
            return f"Brightness set to {level}%"
        return "No brightness control found."
    except ImportError:
        return f"Brightness control requires wmi. Install: pip install wmi"
    except Exception as e:
        return f"Error setting brightness: {e}"


def _brightness_mac(level: int) -> str:
    """macOS brightness control."""
    if level < 0:
        result = subprocess.run(
            ["osascript", "-e", "tell application \"System Events\" to return brightness of display 1"],
            capture_output=True, text=True,
        )
        return f"Current brightness: {result.stdout.strip()}"

    level = max(0, min(100, level))
    scaled = level * 100
    subprocess.run(["brightness", str(level / 100)])
    return f"Brightness set to {level}%"


def _brightness_linux(level: int) -> str:
    """Linux brightness control."""
    brightness_paths = [
        "/sys/class/backlight/amdgpu1/brightness",
        "/sys/class/backlight/intel_backlight/brightness",
        "/sys/class/backlight/acpi_video0/brightness",
    ]
    max_paths = [
        "/sys/class/backlight/amdgpu1/max_brightness",
        "/sys/class/backlight/intel_backlight/max_brightness",
        "/sys/class/backlight/acpi_video0/max_brightness",
    ]

    for bpath, mpath in zip(brightness_paths, max_paths):
        if os.path.exists(bpath) and os.path.exists(mpath):
            if level < 0:
                with open(bpath) as f:
                    current = int(f.read().strip())
                with open(mpath) as f:
                    max_b = int(f.read().strip())
                pct = int(current / max_b * 100)
                return f"Current brightness: {pct}%"

            with open(mpath) as f:
                max_b = int(f.read().strip())
            target = int(level / 100 * max_b)
            try:
                with open(bpath, "w") as f:
                    f.write(str(target))
                return f"Brightness set to {level}%"
            except PermissionError:
                return f"Permission denied. Try: sudo brightness {level}"

    return "No brightness control found on this system."


@tool
def system_info() -> str:
    """Get comprehensive system information.

    Returns:
        A formatted string with system details including OS, CPU, memory, and disk info.
    """
    try:
        info: list[str] = []
        info.append(f"OS: {platform.system()} {platform.release()} ({platform.version()})")
        info.append(f"Machine: {platform.machine()}")
        info.append(f"Processor: {platform.processor() or 'Unknown'}")
        info.append(f"Python: {platform.python_version()}")

        try:
            import psutil
            mem = psutil.virtual_memory()
            info.append(f"RAM Total: {mem.total / (1024**3):.1f} GB")
            info.append(f"RAM Used: {mem.percent}%")

            disk = psutil.disk_usage("/")
            info.append(f"Disk Total: {disk.total / (1024**3):.1f} GB")
            info.append(f"Disk Used: {disk.percent}%")

            cpu_pct = psutil.cpu_percent(interval=0.5)
            info.append(f"CPU Usage: {cpu_pct}%")
            info.append(f"CPU Cores: {psutil.cpu_count(logical=False)} physical, {psutil.cpu_count()} logical")
        except ImportError:
            info.append("Install psutil for detailed system info: pip install psutil")

        return "\n".join(info)

    except Exception as e:
        return f"Error getting system info: {e}"


@tool
def execute_command(command: str) -> str:
    """Execute a system command (with safety filtering).

    Args:
        command: The command to execute. Dangerous commands are blocked.

    Returns:
        The command output or an error message.
    """
    if not command or not command.strip():
        return "Error: Command cannot be empty."

    command = command.strip()

    if not _is_command_safe(command):
        return (
            "Error: This command is blocked for safety reasons.\n"
            "Blocked commands include: format, del, rm, shutdown, regedit, etc."
        )

    try:
        if _WIN:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=30, encoding="utf-8", errors="replace",
            )
        else:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=30,
            )

        output = result.stdout
        if result.stderr:
            output += f"\n[STDERR]: {result.stderr}"

        if len(output) > 5000:
            output = output[:5000] + "\n... [truncated]"

        return output if output else "Command executed (no output)."

    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"Error executing command: {e}"


@tool
def open_website(url: str) -> str:
    """Open a URL in the default web browser.

    Args:
        url: The URL to open.

    Returns:
        A success or error message.
    """
    if not url or not url.strip():
        return "Error: URL cannot be empty."

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        import webbrowser
        webbrowser.open(url)
        return f"Opened in browser: {url}"
    except Exception as e:
        return f"Error opening URL: {e}"


@tool
def screenshot() -> str:
    """Take a screenshot of the current screen and save it.

    Returns:
        The path to the saved screenshot.
    """
    try:
        from pathlib import Path

        desktop = Path.home() / "Desktop"
        timestamp_str = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp_str}.png"
        filepath = desktop / filename

        if _WIN:
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab()
                img.save(str(filepath))
                return f"Screenshot saved: {filepath}"
            except ImportError:
                return (
                    "Screenshot requires Pillow. Install: pip install Pillow\n"
                    "Alternative: Use Win+Shift+S to take a screenshot manually."
                )
        elif _MAC:
            subprocess.run(["screencapture", str(filepath)])
            return f"Screenshot saved: {filepath}"
        else:
            subprocess.run(["gnome-screenshot", "-f", str(filepath)])
            return f"Screenshot saved: {filepath}"

    except Exception as e:
        return f"Error taking screenshot: {e}"


system_tools = [
    open_application, close_application, control_volume,
    control_brightness, system_info, execute_command,
    open_website, screenshot,
]
