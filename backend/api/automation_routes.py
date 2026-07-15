"""Automation routes for system control, app management, and web automation."""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import webbrowser
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.auth import get_current_user
from backend.schemas.schemas import AutomationCommand, AutomationResponse
from database.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/automation", tags=["Automation"])

_SYSTEM = platform.system().lower()


def _launch_app(app_name: str) -> bool:
    """Attempt to launch an application by name."""
    try:
        if _SYSTEM == "windows":
            os.startfile(app_name)
            return True
        elif _SYSTEM == "darwin":
            subprocess.Popen(["open", "-a", app_name])
            return True
        else:
            subprocess.Popen([app_name])
            return True
    except Exception as exc:
        logger.error("Failed to launch %s: %s", app_name, exc)
        return False


def _close_app(app_name: str) -> bool:
    """Attempt to close an application by name."""
    try:
        if _SYSTEM == "windows":
            subprocess.run(["taskkill", "/IM", f"{app_name}.exe", "/F"], capture_output=True)
            return True
        elif _SYSTEM == "darwin":
            subprocess.run(["osascript", "-e", f'quit app "{app_name}"'], capture_output=True)
            return True
        else:
            subprocess.run(["pkill", "-f", app_name], capture_output=True)
            return True
    except Exception as exc:
        logger.error("Failed to close %s: %s", app_name, exc)
        return False


def _run_system_command(command: str) -> Dict[str, Any]:
    """Execute a system shell command and return output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "stdout": result.stdout[:10000],
            "stderr": result.stderr[:5000],
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Command timed out after 30s", "returncode": -1}
    except Exception as exc:
        return {"stdout": "", "stderr": str(exc), "returncode": -1}


@router.get("/capabilities")
async def get_capabilities(current_user: User = Depends(get_current_user)):
    """Return available automation capabilities based on the OS."""
    return {
        "platform": _SYSTEM,
        "capabilities": {
            "app_launch": True,
            "app_close": True,
            "web_open": True,
            "system_command": True,
            "clipboard": _SYSTEM in ("windows", "darwin", "linux"),
            "screenshots": _SYSTEM in ("windows", "darwin", "linux"),
        },
    }


@router.post("/execute", response_model=AutomationResponse)
async def execute_command(
    body: AutomationCommand,
    current_user: User = Depends(get_current_user),
):
    """Execute a generic automation command."""
    cmd = body.command.lower().strip()
    params = body.parameters or {}

    if cmd.startswith("open ") or cmd.startswith("launch "):
        app = cmd.split(None, 1)[1]
        success = _launch_app(app)
        return AutomationResponse(
            success=success,
            message=f"Launched {app}" if success else f"Failed to launch {app}",
        )
    elif cmd.startswith("close ") or cmd.startswith("quit "):
        app = cmd.split(None, 1)[1]
        success = _close_app(app)
        return AutomationResponse(
            success=success,
            message=f"Closed {app}" if success else f"Failed to close {app}",
        )
    elif cmd.startswith("open url ") or cmd.startswith("browse "):
        url = cmd.split(None, 2)[-1] if " " in cmd else params.get("url", "")
        webbrowser.open(url)
        return AutomationResponse(success=True, message=f"Opened {url}")
    else:
        result = _run_system_command(body.command)
        return AutomationResponse(
            success=result["returncode"] == 0,
            message=result["stdout"] or result["stderr"],
            data=result,
        )


@router.post("/app/launch", response_model=AutomationResponse)
async def launch_application(
    body: AutomationCommand,
    current_user: User = Depends(get_current_user),
):
    """Launch an application."""
    app_name = body.parameters.get("name", body.command) if body.parameters else body.command
    success = _launch_app(app_name)
    return AutomationResponse(
        success=success,
        message=f"Launched {app_name}" if success else f"Failed to launch {app_name}",
    )


@router.post("/app/close", response_model=AutomationResponse)
async def close_application(
    body: AutomationCommand,
    current_user: User = Depends(get_current_user),
):
    """Close an application."""
    app_name = body.parameters.get("name", body.command) if body.parameters else body.command
    success = _close_app(app_name)
    return AutomationResponse(
        success=success,
        message=f"Closed {app_name}" if success else f"Failed to close {app_name}",
    )


@router.post("/web/open", response_model=AutomationResponse)
async def open_web(
    body: AutomationCommand,
    current_user: User = Depends(get_current_user),
):
    """Open a URL in the default browser."""
    url = body.parameters.get("url", body.command) if body.parameters else body.command
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return AutomationResponse(success=True, message=f"Opened {url}")


@router.post("/system/command", response_model=AutomationResponse)
async def system_command(
    body: AutomationCommand,
    current_user: User = Depends(get_current_user),
):
    """Execute a safe system command (allowlisted only)."""
    import re as _re

    SAFE_COMMANDS = {
        "dir", "ls", "pwd", "whoami", "hostname", "date", "time",
        "echo", "cat", "head", "tail", "wc", "df", "du", "free",
        "uname", "uptime", "tasklist", "taskmgr", "systeminfo",
        "ipconfig", "ifconfig", "ping", "tracert", "nslookup",
        "python", "python3", "node", "npm", "pip",
    }

    cmd = body.command.strip()
    base_cmd = cmd.split()[0].lower() if cmd.split() else ""
    base_cmd = _re.sub(r'^.*/', '', base_cmd)

    if base_cmd not in SAFE_COMMANDS:
        return AutomationResponse(
            success=False,
            message=f"Command '{base_cmd}' is not in the safe commands allowlist. "
                    f"Allowed: {', '.join(sorted(SAFE_COMMANDS))}",
        )

    for pattern in ["&&", "||", ";", "|", "`", "$(", "${"]:
        if pattern in cmd:
            return AutomationResponse(
                success=False,
                message=f"Command contains blocked operator: {pattern}",
            )

    result = _run_system_command(cmd)
    return AutomationResponse(
        success=result["returncode"] == 0,
        message=result["stdout"] or result["stderr"],
        data=result,
    )
