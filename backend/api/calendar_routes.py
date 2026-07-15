"""Calendar routes."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from database.connection import get_db
from database.models import CalendarEvent, User
from backend.schemas.schemas import CalendarEventCreate, CalendarEventResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calendar", tags=["Calendar"])


@router.get("", response_model=list[CalendarEventResponse])
async def list_events(
    start: datetime | None = None,
    end: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List calendar events within a date range."""
    conditions = [CalendarEvent.user_id == current_user.id]
    if start:
        conditions.append(CalendarEvent.end_time >= start)
    if end:
        conditions.append(CalendarEvent.start_time <= end)
    q = (
        select(CalendarEvent)
        .where(and_(*conditions))
        .order_by(CalendarEvent.start_time)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/today", response_model=list[CalendarEventResponse])
async def today_events(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return events scheduled for today."""
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    q = (
        select(CalendarEvent)
        .where(
            CalendarEvent.user_id == current_user.id,
            CalendarEvent.start_time < end,
            CalendarEvent.end_time > start,
        )
        .order_by(CalendarEvent.start_time)
    )
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/week", response_model=list[CalendarEventResponse])
async def week_events(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return events for the current week."""
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=now.weekday())
    end = start + timedelta(days=7)
    q = (
        select(CalendarEvent)
        .where(
            CalendarEvent.user_id == current_user.id,
            CalendarEvent.start_time < end,
            CalendarEvent.end_time > start,
        )
        .order_by(CalendarEvent.start_time)
    )
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/conflicts", response_model=list[dict])
async def check_conflicts(
    start: datetime = Query(...),
    end: datetime = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Find events that overlap with the given time range."""
    q = select(CalendarEvent).where(
        CalendarEvent.user_id == current_user.id,
        CalendarEvent.start_time < end,
        CalendarEvent.end_time > start,
    )
    result = await db.execute(q)
    conflicts = result.scalars().all()
    return [
        {
            "id": e.id,
            "title": e.title,
            "start_time": e.start_time.isoformat(),
            "end_time": e.end_time.isoformat(),
        }
        for e in conflicts
    ]


@router.post("", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    body: CalendarEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new calendar event."""
    if body.end_time <= body.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")
    event = CalendarEvent(
        user_id=current_user.id,
        title=body.title,
        description=body.description,
        start_time=body.start_time,
        end_time=body.end_time,
        location=body.location,
        attendees=body.attendees,
        recurrence=body.recurrence,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


@router.get("/{event_id}", response_model=CalendarEventResponse)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single calendar event."""
    result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.id == event_id, CalendarEvent.user_id == current_user.id
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.patch("/{event_id}", response_model=CalendarEventResponse)
async def update_event(
    event_id: int,
    body: CalendarEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a calendar event."""
    result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.id == event_id, CalendarEvent.user_id == current_user.id
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    for field, value in body.model_dump().items():
        setattr(event, field, value)
    await db.flush()
    await db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a calendar event."""
    result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.id == event_id, CalendarEvent.user_id == current_user.id
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    await db.delete(event)


@router.post("/sync", response_model=dict)
async def sync_google_calendar(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sync events from Google Calendar (stub – requires OAuth setup)."""
    logger.info("Google Calendar sync requested by user %s", current_user.id)
    return {"status": "sync_requested", "message": "Google Calendar sync requires OAuth credentials. Configure GOOGLE_CALENDAR_CREDENTIALS_PATH."}
