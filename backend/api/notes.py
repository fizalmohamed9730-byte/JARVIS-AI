"""Notes routes with search and tag management."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from database.connection import get_db
from database.models import Note, User
from backend.schemas.schemas import NoteCreate, NoteResponse, NoteUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notes", tags=["Notes"])


@router.get("", response_model=list[NoteResponse])
async def list_notes(
    category: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List notes, optionally filtered by category."""
    conditions = [Note.user_id == current_user.id]
    if category:
        conditions.append(Note.category == category)
    q = (
        select(Note)
        .where(*conditions)
        .order_by(Note.is_pinned.desc(), Note.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/pinned", response_model=list[NoteResponse])
async def list_pinned_notes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List pinned notes."""
    q = (
        select(Note)
        .where(Note.user_id == current_user.id, Note.is_pinned.is_(True))
        .order_by(Note.updated_at.desc())
    )
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/search", response_model=list[NoteResponse])
async def search_notes(
    q: str = Query(..., min_length=1, max_length=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full-text search across notes title and content."""
    search_pattern = f"%{q}%"
    query = (
        select(Note)
        .where(
            Note.user_id == current_user.id,
            or_(
                Note.title.ilike(search_pattern),
                Note.content.ilike(search_pattern),
            ),
        )
        .order_by(Note.updated_at.desc())
        .limit(50)
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/tags", response_model=list[str])
async def list_all_tags(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a deduplicated list of all tags used across the user's notes."""
    q = select(Note.tags).where(Note.user_id == current_user.id, Note.tags.isnot(None))
    result = await db.execute(q)
    all_tags: set[str] = set()
    for row in result.scalars().all():
        if isinstance(row, list):
            all_tags.update(row)
    return sorted(all_tags)


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    body: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new note."""
    note = Note(
        user_id=current_user.id,
        title=body.title,
        content=body.content,
        tags=body.tags,
        category=body.category,
        is_pinned=body.is_pinned,
    )
    db.add(note)
    await db.flush()
    await db.refresh(note)
    return note


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single note."""
    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.user_id == current_user.id)
    )
    note = result.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: int,
    body: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a note."""
    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.user_id == current_user.id)
    )
    note = result.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    await db.flush()
    await db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a note."""
    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.user_id == current_user.id)
    )
    note = result.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    await db.delete(note)
