"""Settings API routes."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from database.connection import get_db
from database.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingsData(BaseModel):
    profile: Optional[Dict[str, Any]] = None
    voice: Optional[Dict[str, Any]] = None
    ai: Optional[Dict[str, Any]] = None
    theme: Optional[Dict[str, Any]] = None
    notifications: Optional[Dict[str, Any]] = None
    apiKeys: Optional[Dict[str, Any]] = None


@router.get("")
async def get_settings(
    current_user: User = Depends(get_current_user),
):
    """Get current user settings."""
    prefs = current_user.preferences or {}
    return prefs


@router.put("")
async def update_settings(
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update current user settings."""
    existing = current_user.preferences or {}
    existing.update(body)
    current_user.preferences = existing
    db.add(current_user)
    await db.flush()
    return {"data": existing, "message": "Settings updated"}
