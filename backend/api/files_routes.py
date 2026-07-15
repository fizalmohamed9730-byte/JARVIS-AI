"""File manager API routes."""

from __future__ import annotations

import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.api.auth import get_current_user
from database.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["Files"])

HOME_DIR = str(Path.home())
DEFAULT_ROOT = str(Path.cwd() / "data" / "workspace")
Path(DEFAULT_ROOT).mkdir(parents=True, exist_ok=True)


class FileItem(BaseModel):
    name: str
    path: str
    type: str
    size: int = 0
    modified: str = ""
    extension: str = ""


class FileOperation(BaseModel):
    source: str
    destination: Optional[str] = None
    name: Optional[str] = None


def _safe_path(requested: str, root: str = DEFAULT_ROOT) -> str:
    """Resolve and validate that the path is within allowed directories."""
    resolved = os.path.realpath(os.path.join(root, requested))
    allowed = [os.path.realpath(DEFAULT_ROOT), os.path.realpath(HOME_DIR)]
    if not any(resolved.startswith(r) for r in allowed):
        raise HTTPException(status_code=403, detail="Access denied to this path")
    return resolved


def _item_info(full_path: str) -> FileItem:
    stat = os.stat(full_path)
    name = os.path.basename(full_path)
    return FileItem(
        name=name,
        path=full_path,
        type="directory" if os.path.isdir(full_path) else "file",
        size=stat.st_size if os.path.isfile(full_path) else 0,
        modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
        extension=os.path.splitext(name)[1].lower() if os.path.isfile(full_path) else "",
    )


@router.get("", response_model=List[FileItem])
async def list_files(
    path: str = Query("", description="Directory path relative to workspace"),
    current_user: User = Depends(get_current_user),
):
    """List files in a directory."""
    full_path = _safe_path(path) if path else DEFAULT_ROOT
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Directory not found")
    if not os.path.isdir(full_path):
        raise HTTPException(status_code=400, detail="Path is not a directory")

    items = []
    try:
        for entry in os.scandir(full_path):
            try:
                items.append(_item_info(entry.path))
            except OSError:
                continue
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    items.sort(key=lambda x: (x.type != "directory", x.name.lower()))
    return items


@router.get("/search", response_model=List[FileItem])
async def search_files(
    q: str = Query(..., min_length=1, description="Search query"),
    path: str = Query("", description="Root directory to search in"),
    current_user: User = Depends(get_current_user),
):
    """Search for files by name."""
    root = _safe_path(path) if path else DEFAULT_ROOT
    if not os.path.exists(root):
        raise HTTPException(status_code=404, detail="Directory not found")

    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames + dirnames:
            if q.lower() in name.lower():
                full = os.path.join(dirpath, name)
                try:
                    results.append(_item_info(full))
                except OSError:
                    continue
                if len(results) >= 100:
                    return results
    return results


@router.get("/read")
async def read_file(
    path: str = Query(..., description="File path"),
    current_user: User = Depends(get_current_user),
):
    """Read file content (text files only)."""
    full_path = _safe_path(path)
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    text_exts = {'.txt', '.md', '.py', '.js', '.ts', '.tsx', '.jsx', '.json', '.yaml',
                 '.yml', '.toml', '.cfg', '.ini', '.html', '.css', '.sql', '.sh',
                 '.bat', '.csv', '.xml', '.log', '.env'}
    ext = os.path.splitext(full_path)[1].lower()
    if ext not in text_exts:
        raise HTTPException(status_code=400, detail="Cannot read non-text files")

    try:
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read(1_000_000)
        return {"content": content, "path": full_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mkdir", status_code=status.HTTP_201_CREATED)
async def create_directory(
    body: FileOperation,
    current_user: User = Depends(get_current_user),
):
    """Create a new directory."""
    target = _safe_path(os.path.join(body.path or "", body.name or "new_folder"))
    if os.path.exists(target):
        raise HTTPException(status_code=409, detail="Directory already exists")
    os.makedirs(target, exist_ok=True)
    return {"success": True, "path": target}


@router.post("/rename")
async def rename_item(
    body: FileOperation,
    current_user: User = Depends(get_current_user),
):
    """Rename a file or directory."""
    source = _safe_path(body.source)
    if not os.path.exists(source):
        raise HTTPException(status_code=404, detail="Source not found")
    if not body.name:
        raise HTTPException(status_code=400, detail="New name required")
    dest = os.path.join(os.path.dirname(source), body.name)
    os.rename(source, dest)
    return {"success": True, "path": dest}


@router.post("/copy")
async def copy_item(
    body: FileOperation,
    current_user: User = Depends(get_current_user),
):
    """Copy a file or directory."""
    source = _safe_path(body.source)
    if not os.path.exists(source):
        raise HTTPException(status_code=404, detail="Source not found")
    dest = _safe_path(body.destination or body.source)
    if os.path.isdir(source):
        shutil.copytree(source, dest)
    else:
        shutil.copy2(source, dest)
    return {"success": True, "path": dest}


@router.post("/move")
async def move_item(
    body: FileOperation,
    current_user: User = Depends(get_current_user),
):
    """Move a file or directory."""
    source = _safe_path(body.source)
    if not os.path.exists(source):
        raise HTTPException(status_code=404, detail="Source not found")
    dest = _safe_path(body.destination or body.source)
    shutil.move(source, dest)
    return {"success": True, "path": dest}


@router.delete("")
async def delete_item(
    path: str = Query(..., description="File or directory path"),
    current_user: User = Depends(get_current_user),
):
    """Delete a file or directory."""
    full_path = _safe_path(path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Not found")
    try:
        import send2trash
        send2trash.send2trash(full_path)
    except ImportError:
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
    return {"success": True, "message": "Moved to trash"}


@router.get("/info")
async def file_info(
    path: str = Query(..., description="File path"),
    current_user: User = Depends(get_current_user),
):
    """Get detailed file information."""
    full_path = _safe_path(path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Not found")
    return _item_info(full_path)
