"""File operation tools for JARVIS AI agent system."""

from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_HOME = Path.home()
_DESKTOP = _HOME / "Desktop"
_DOCUMENTS = _HOME / "Documents"
_DOWNLOADS = _HOME / "Downloads"

_UNSAFE_PATTERNS = {
    "\\System32",
    "\\Windows",
    "/etc",
    "/usr",
    "/bin",
    "/sbin",
    "/boot",
    "/root",
    "C:\\Windows",
}


def _is_safe_path(path: str) -> bool:
    """Check if a path is safe to operate on."""
    resolved = os.path.realpath(path)
    for pattern in _UNSAFE_PATTERNS:
        if resolved.lower().replace("/", "\\").startswith(pattern.lower().replace("/", "\\")):
            return False
    return True


def _normalize_path(path: str) -> str:
    """Expand ~ and normalize the path."""
    path = os.path.expanduser(path)
    path = os.path.normpath(path)
    return path


@tool
def search_files(
    name: str = "",
    extension: str = "",
    path: str = "",
    date_range: str = "",
    max_results: int = 50,
) -> str:
    """Search for files on the system.

    Args:
        name: Filename pattern to search for (supports partial matches).
        extension: File extension filter (e.g., 'pdf', 'docx', 'py').
        path: Directory to search in. Defaults to user home directory.
        date_range: Date range filter in format 'YYYY-MM-DD:YYYY-MM-DD'.
        max_results: Maximum number of results. Defaults to 50.

    Returns:
        A formatted list of matching files with paths, sizes, and dates.
    """
    search_path = _normalize_path(path) if path else str(_HOME)

    if not os.path.isdir(search_path):
        return f"Error: Directory not found: {search_path}"

    if not _is_safe_path(search_path):
        return "Error: Cannot search in system directories for safety reasons."

    date_start = None
    date_end = None
    if date_range and ":" in date_range:
        try:
            parts = date_range.split(":")
            date_start = datetime.strptime(parts[0].strip(), "%Y-%m-%d")
            date_end = datetime.strptime(parts[1].strip(), "%Y-%m-%d")
        except ValueError:
            return "Error: Invalid date range format. Use 'YYYY-MM-DD:YYYY-MM-DD'."

    found_files: list[dict[str, Any]] = []
    search_name = name.lower() if name else ""
    search_ext = extension.lower().strip(".")

    try:
        for root, dirs, files in os.walk(search_path):
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
                and d not in {"node_modules", "__pycache__", ".git", ".venv", "venv"}
            ]

            for fname in files:
                if len(found_files) >= max_results:
                    break

                if search_name and search_name not in fname.lower():
                    continue

                if search_ext and not fname.lower().endswith(f".{search_ext}"):
                    continue

                full_path = os.path.join(root, fname)

                try:
                    stat = os.stat(full_path)
                except OSError:
                    continue

                mod_time = datetime.fromtimestamp(stat.st_mtime)

                if date_start and mod_time < date_start:
                    continue
                if date_end and mod_time > date_end:
                    continue

                found_files.append({
                    "name": fname,
                    "path": full_path,
                    "size_bytes": stat.st_size,
                    "modified": mod_time.strftime("%Y-%m-%d %H:%M"),
                    "extension": os.path.splitext(fname)[1],
                })

            if len(found_files) >= max_results:
                break

    except PermissionError:
        return f"Error: Permission denied accessing {search_path}"
    except Exception as e:
        return f"Error searching files: {e}"

    if not found_files:
        return "No matching files found."

    formatted = []
    for i, f in enumerate(found_files, 1):
        size = f["size_bytes"]
        if size > 1_048_576:
            size_str = f"{size / 1_048_576:.1f} MB"
        elif size > 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size} B"

        formatted.append(
            f"{i}. {f['name']}\n"
            f"   Path: {f['path']}\n"
            f"   Size: {size_str} | Modified: {f['modified']}\n"
        )

    return "\n".join(formatted)


@tool
def read_file(path: str, max_length: int = 10000) -> str:
    """Read and return the content of a file.

    Args:
        path: Path to the file to read.
        max_length: Maximum characters to read. Defaults to 10000.

    Returns:
        The text content of the file, or an error message.
    """
    path = _normalize_path(path)

    if not os.path.isfile(path):
        return f"Error: File not found: {path}"

    if not _is_safe_path(path):
        return "Error: Cannot read system files for safety reasons."

    text_extensions = {
        ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
        ".json", ".yaml", ".yml", ".toml", ".xml", ".csv", ".log", ".ini",
        ".cfg", ".conf", ".sh", ".bat", ".ps1", ".env", ".gitignore",
        ".sql", ".r", ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".go",
        ".rs", ".swift", ".kt", ".scala", ".rb", ".php", ".pl", ".lua",
    }

    ext = os.path.splitext(path)[1].lower()
    if ext and ext not in text_extensions:
        return f"Cannot read binary file ({ext}). Supported: {', '.join(sorted(text_extensions))}"

    try:
        size = os.path.getsize(path)
        if size > 10_485_76:
            return f"Error: File too large ({size / 1_048_576:.1f} MB). Max supported: 10 MB."

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_length)

        if size > max_length:
            content += f"\n\n... [truncated at {max_length} chars, total: {size}]"

        return content

    except PermissionError:
        return f"Error: Permission denied reading {path}"
    except Exception as e:
        return f"Error reading file: {e}"


@tool
def create_file(path: str, content: str, overwrite: bool = False) -> str:
    """Create a new file with the given content.

    Args:
        path: Path where the file should be created.
        content: The content to write to the file.
        overwrite: Whether to overwrite an existing file. Defaults to False.

    Returns:
        A success message with file details or an error message.
    """
    path = _normalize_path(path)

    if not _is_safe_path(path):
        return "Error: Cannot create files in system directories for safety reasons."

    if os.path.exists(path) and not overwrite:
        return f"Error: File already exists at {path}. Set overwrite=true to replace it."

    try:
        parent = os.path.dirname(path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        size = os.path.getsize(path)
        return f"File created successfully: {path} ({size} bytes)"

    except PermissionError:
        return f"Error: Permission denied creating {path}"
    except Exception as e:
        return f"Error creating file: {e}"


@tool
def move_file(source: str, destination: str) -> str:
    """Move or rename a file.

    Args:
        source: Path of the file to move.
        destination: Destination path or directory.

    Returns:
        A success message or an error message.
    """
    source = _normalize_path(source)
    destination = _normalize_path(destination)

    if not os.path.isfile(source):
        return f"Error: Source file not found: {source}"

    if not _is_safe_path(source) or not _is_safe_path(destination):
        return "Error: Cannot move files to/from system directories."

    if os.path.isdir(destination):
        destination = os.path.join(destination, os.path.basename(source))

    if os.path.exists(destination):
        return f"Error: Destination already exists: {destination}"

    try:
        shutil.move(source, destination)
        return f"File moved: {source} -> {destination}"
    except PermissionError:
        return f"Error: Permission denied moving file"
    except Exception as e:
        return f"Error moving file: {e}"


@tool
def delete_file(path: str, confirm: bool = False) -> str:
    """Delete a file. Requires confirmation for safety.

    Args:
        path: Path of the file to delete.
        confirm: Must be True to actually delete. Defaults to False.

    Returns:
        A success message or an error/warning message.
    """
    path = _normalize_path(path)

    if not os.path.isfile(path):
        return f"Error: File not found: {path}"

    if not _is_safe_path(path):
        return "Error: Cannot delete system files."

    important_dirs = {
        str(_DESKTOP), str(_DOCUMENTS), str(_DOWNLOADS),
        str(_HOME),
    }
    parent = os.path.dirname(os.path.abspath(path))
    if parent in important_dirs:
        if not confirm:
            return (
                f"WARNING: About to delete a file in an important directory: {path}\n"
                "Re-run with confirm=true to proceed."
            )

    if not confirm:
        return f"File will be deleted: {path}\nRe-run with confirm=true to proceed."

    try:
        os.remove(path)
        return f"File deleted: {path}"
    except PermissionError:
        return f"Error: Permission denied deleting {path}"
    except Exception as e:
        return f"Error deleting file: {e}"


@tool
def generate_document(
    doc_type: str,
    content: str,
    filename: str,
    output_dir: str = "",
) -> str:
    """Generate a document file (text-based formats).

    Args:
        doc_type: Type of document ('txt', 'md', 'csv', 'json', 'html').
        content: The content of the document.
        filename: Name of the file (without extension).
        output_dir: Directory to save the file. Defaults to Desktop.

    Returns:
        A success message with the path to the generated file.
    """
    supported_types = {"txt", "md", "csv", "json", "html"}
    if doc_type.lower() not in supported_types:
        return f"Error: Unsupported doc type '{doc_type}'. Supported: {', '.join(sorted(supported_types))}"

    out_dir = _normalize_path(output_dir) if output_dir else str(_DESKTOP)
    if not os.path.isdir(out_dir):
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            return f"Error creating output directory: {e}"

    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
    filepath = os.path.join(out_dir, f"{safe_name}.{doc_type}")

    if doc_type == "html" and "<html" not in content.lower():
        content = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{safe_name}</title>
<style>body{{font-family:sans-serif;max-width:800px;margin:0 auto;padding:20px;}}</style>
</head>
<body>{content}</body>
</html>"""

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        size = os.path.getsize(filepath)
        return f"Document created: {filepath} ({size} bytes)"

    except Exception as e:
        return f"Error generating document: {e}"


file_tools = [search_files, read_file, create_file, move_file, delete_file, generate_document]
