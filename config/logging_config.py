"""Structured logging configuration for JARVIS."""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from config.settings import settings


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_data"):
            log_entry["extra"] = record.extra_data
        return json.dumps(log_entry, default=str)


class ConsoleFormatter(logging.Formatter):
    """Colored console formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[1;31m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = (
            f"{color}{timestamp} | {record.levelname:<8}{self.RESET} "
            f"| {record.name:<25} | {record.getMessage()}"
        )
        if record.exc_info and record.exc_info[0] is not None:
            message += f"\n{self.formatException(record.exc_info)}"
        return message


def setup_logging() -> None:
    """Configure logging for the entire application."""
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    is_debug = settings.debug or settings.log_level.upper() == "DEBUG"

    if is_debug:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(ConsoleFormatter())
        root_logger.addHandler(console_handler)
    else:
        json_handler = logging.StreamHandler(sys.stdout)
        json_handler.setLevel(logging.INFO)
        json_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(json_handler)

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "jarvis.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)

    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "jarvis_error.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_handler)

    for module_name in [
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "sqlalchemy.engine",
        "httpx",
        "httpcore",
    ]:
        module_logger = logging.getLogger(module_name)
        if module_name.startswith("uvicorn") and not is_debug:
            module_logger.setLevel(logging.WARNING)
        elif module_name.startswith("uvicorn"):
            module_logger.setLevel(logging.INFO)
        else:
            module_logger.setLevel(logging.WARNING)

    logging.getLogger("config").setLevel(logging.INFO)
    logging.getLogger("database").setLevel(logging.INFO)
    logging.getLogger("backend").setLevel(logging.DEBUG if is_debug else logging.INFO)
    logging.getLogger("services").setLevel(logging.DEBUG if is_debug else logging.INFO)
