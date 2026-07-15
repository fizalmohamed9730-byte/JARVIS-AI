"""File management system with search, CRUD, and organization capabilities."""

import datetime
import fnmatch
import logging
import os
import shutil
import send2trash
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


class FileManager:
    """Provides comprehensive file management operations.

    All destructive operations (delete, move, overwrite) use the system trash
    rather than permanent deletion to allow recovery.
    """

    # --------------------------------------------------------------------- #
    # Search
    # --------------------------------------------------------------------- #

    def search_files(
        self,
        query: str = "",
        path: str = "",
        extension: str = "",
        date_range: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for files matching criteria.

        Args:
            query: Substring or glob pattern to match against filenames.
            path: Root directory to search from. Defaults to user home.
            extension: File extension filter (e.g. ``".py"``).
            date_range: ISO date range like ``"2024-01-01:2024-12-31"``.

        Returns:
            List of file metadata dictionaries.
        """
        search_root = Path(path) if path else Path.home()
        if not search_root.is_dir():
            logger.warning("Search path does not exist: %s", search_root)
            return []

        start_date: Optional[datetime.datetime] = None
        end_date: Optional[datetime.datetime] = None
        if date_range and ":" in date_range:
            parts = date_range.split(":")
            try:
                start_date = datetime.datetime.fromisoformat(parts[0].strip())
                end_date = datetime.datetime.fromisoformat(parts[1].strip())
            except ValueError:
                logger.warning("Invalid date_range format: %s", date_range)

        results: List[Dict[str, Any]] = []
        max_results = 500

        for root, dirs, files in os.walk(search_root):
            for filename in files:
                if len(results) >= max_results:
                    return results

                if extension and not filename.lower().endswith(extension.lower()):
                    continue

                if query and not fnmatch.fnmatch(filename.lower(), f"*{query.lower()}*"):
                    continue

                filepath = os.path.join(root, filename)
                try:
                    stat = os.stat(filepath)
                    mtime = datetime.datetime.fromtimestamp(stat.st_mtime)

                    if start_date and mtime < start_date:
                        continue
                    if end_date and mtime > end_date:
                        continue

                    results.append({
                        "path": filepath,
                        "name": filename,
                        "size": stat.st_size,
                        "modified": mtime.isoformat(),
                        "extension": os.path.splitext(filename)[1],
                    })
                except (PermissionError, OSError):
                    continue

        results.sort(key=lambda x: x["modified"], reverse=True)
        return results

    # --------------------------------------------------------------------- #
    # CRUD
    # --------------------------------------------------------------------- #

    def read_file(self, path: str) -> str:
        """Read and return the text content of a file.

        Args:
            path: Absolute path to the file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file appears to be binary.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {path}")

        # Check for binary content
        try:
            with open(p, "rb") as f:
                chunk = f.read(8192)
                if b"\x00" in chunk:
                    raise ValueError(f"Binary file detected, cannot read as text: {path}")
        except ValueError:
            raise
        except Exception:
            pass

        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def create_file(self, path: str, content: str = "") -> Dict[str, Any]:
        """Create a new file with optional content.

        Creates parent directories as needed. Fails if the file already exists.

        Args:
            path: Absolute path for the new file.
            content: Initial text content.
        """
        p = Path(path)
        if p.exists():
            return {"success": False, "error": f"File already exists: {path}"}

        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("Created file: %s", path)
        return {"success": True, "path": str(p), "size": p.stat().st_size}

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to a file, creating it if it doesn't exist.

        Args:
            path: Absolute path to the file.
            content: Text content to write.
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("Wrote %d bytes to %s", len(content), path)
        return {"success": True, "path": str(p), "size": p.stat().st_size}

    def move_file(self, source: str, dest: str) -> Dict[str, Any]:
        """Move a file from *source* to *dest*."""
        src = Path(source)
        if not src.exists():
            return {"success": False, "error": f"Source not found: {source}"}

        dst = Path(dest)
        dst.parent.mkdir(parents=True, exist_ok=True)

        if dst.exists():
            logger.warning("Overwriting existing file: %s", dest)
            send2trash.send2trash(str(dst))

        shutil.move(str(src), str(dst))
        logger.info("Moved %s -> %s", source, dest)
        return {"success": True, "source": str(src), "dest": str(dst)}

    def copy_file(self, source: str, dest: str) -> Dict[str, Any]:
        """Copy a file from *source* to *dest*."""
        src = Path(source)
        if not src.exists():
            return {"success": False, "error": f"Source not found: {source}"}

        dst = Path(dest)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        logger.info("Copied %s -> %s", source, dest)
        return {"success": True, "source": str(src), "dest": str(dst)}

    def delete_file(self, path: str) -> Dict[str, Any]:
        """Move a file to trash (not permanent delete) for safe recovery."""
        p = Path(path)
        if not p.exists():
            return {"success": False, "error": f"File not found: {path}"}

        try:
            send2trash.send2trash(str(p))
            logger.info("Moved to trash: %s", path)
            return {"success": True, "path": str(p), "message": "Moved to trash"}
        except Exception as exc:
            # Fallback to permanent delete if send2trash fails
            logger.warning("send2trash failed, using permanent delete: %s", exc)
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                shutil.rmtree(str(p))
            return {"success": True, "path": str(p), "message": "Permanently deleted"}

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Return metadata about a file."""
        p = Path(path)
        if not p.exists():
            return {"exists": False, "error": f"File not found: {path}"}

        stat = p.stat()
        return {
            "exists": True,
            "path": str(p.resolve()),
            "name": p.name,
            "extension": p.suffix,
            "is_file": p.is_file(),
            "is_dir": p.is_dir(),
            "size": stat.st_size,
            "size_human": self._human_size(stat.st_size),
            "created": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "accessed": datetime.datetime.fromtimestamp(stat.st_atime).isoformat(),
            "readable": os.access(str(p), os.R_OK),
            "writable": os.access(str(p), os.W_OK),
        }

    # --------------------------------------------------------------------- #
    # Batch / Organization
    # --------------------------------------------------------------------- #

    def batch_rename(
        self, pattern: str, replacement: str, path: str = ""
    ) -> Dict[str, Any]:
        """Rename files in *path* matching *pattern* using *replacement*.

        Uses simple string replacement on filenames.

        Args:
            pattern: Substring in filenames to find.
            replacement: Replacement string.
            path: Directory to operate on. Defaults to current directory.
        """
        directory = Path(path) if path else Path.cwd()
        if not directory.is_dir():
            return {"success": False, "error": f"Directory not found: {path}"}

        renamed: List[Dict[str, str]] = []
        for p in directory.iterdir():
            if pattern in p.name:
                new_name = p.name.replace(pattern, replacement)
                new_path = p.parent / new_name
                try:
                    p.rename(new_path)
                    renamed.append({"from": p.name, "to": new_name})
                except Exception as exc:
                    logger.warning("Failed to rename %s: %s", p.name, exc)

        logger.info("Batch renamed %d files in %s", len(renamed), directory)
        return {"success": True, "renamed": renamed, "count": len(renamed)}

    def organize_folder(
        self, path: str, rules: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """Organize files in *path* into subfolders by extension.

        Default rules sort common file types into categories. Custom rules can
        be provided as ``{folder_name: [extensions]}``.

        Args:
            path: Directory to organize.
            rules: Optional mapping of folder names to file extensions.
        """
        directory = Path(path)
        if not directory.is_dir():
            return {"success": False, "error": f"Directory not found: {path}"}

        if rules is None:
            rules = {
                "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".md"],
                "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico"],
                "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"],
                "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
                "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
                "Code": [".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".h", ".go", ".rs"],
                "Spreadsheets": [".xls", ".xlsx", ".csv", ".tsv"],
                "Presentations": [".ppt", ".pptx", ".key"],
                "Executables": [".exe", ".msi", ".dmg", ".app", ".deb", ".rpm"],
            }

        # Build reverse lookup: extension -> folder
        ext_map: Dict[str, str] = {}
        for folder, extensions in rules.items():
            for ext in extensions:
                ext_map[ext.lower()] = folder

        moved: List[Dict[str, str]] = []
        for p in directory.iterdir():
            if p.is_dir():
                continue

            ext = p.suffix.lower()
            folder_name = ext_map.get(ext, "Other")
            target_dir = directory / folder_name
            target_dir.mkdir(exist_ok=True)

            target_path = target_dir / p.name
            if target_path.exists():
                # Avoid overwriting
                stem = p.stem
                suffix = p.suffix
                counter = 1
                while target_path.exists():
                    target_path = target_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

            try:
                shutil.move(str(p), str(target_path))
                moved.append({"from": p.name, "to": f"{folder_name}/{target_path.name}"})
            except Exception as exc:
                logger.warning("Failed to move %s: %s", p.name, exc)

        logger.info("Organized %d files in %s", len(moved), directory)
        return {"success": True, "moved": moved, "count": len(moved)}

    def get_recent_files(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the most recently modified files across common user directories."""
        search_dirs = [
            Path.home() / "Documents",
            Path.home() / "Desktop",
            Path.home() / "Downloads",
        ]

        all_files: List[Dict[str, Any]] = []
        for search_dir in search_dirs:
            if not search_dir.is_dir():
                continue
            for p in search_dir.rglob("*"):
                if p.is_file():
                    try:
                        stat = p.stat()
                        all_files.append({
                            "path": str(p),
                            "name": p.name,
                            "size": stat.st_size,
                            "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "extension": p.suffix,
                        })
                    except (PermissionError, OSError):
                        continue

        all_files.sort(key=lambda x: x["modified"], reverse=True)
        return all_files[:limit]

    # --------------------------------------------------------------------- #
    # Helpers
    # --------------------------------------------------------------------- #

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        """Convert bytes to human-readable string."""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(size_bytes) < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024  # type: ignore[assignment]
        return f"{size_bytes:.1f} PB"
