"""Central calendar manager for event CRUD, conflict detection, and free-slot discovery."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


class CalendarEvent:
    """Represents a single calendar event with all associated metadata."""

    def __init__(
        self,
        event_id: str,
        title: str,
        start: datetime,
        end: datetime,
        description: str = "",
        location: str = "",
        attendees: Optional[List[str]] = None,
        all_day: bool = False,
        recurring: bool = False,
        recurrence_rule: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.event_id = event_id
        self.title = title
        self.start = start
        self.end = end
        self.description = description
        self.location = location
        self.attendees = attendees or []
        self.all_day = all_day
        self.recurring = recurring
        self.recurrence_rule = recurrence_rule
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "description": self.description,
            "location": self.location,
            "attendees": self.attendees,
            "all_day": self.all_day,
            "recurring": self.recurring,
            "recurrence_rule": self.recurrence_rule,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CalendarEvent":
        start = data["start"]
        end = data["end"]
        if isinstance(start, str):
            start = datetime.fromisoformat(start)
        if isinstance(end, str):
            end = datetime.fromisoformat(end)
        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            title=data.get("title", ""),
            start=start,
            end=end,
            description=data.get("description", ""),
            location=data.get("location", ""),
            attendees=data.get("attendees", []),
            all_day=data.get("all_day", False),
            recurring=data.get("recurring", False),
            recurrence_rule=data.get("recurrence_rule", ""),
            metadata=data.get("metadata", {}),
        )

    def overlaps(self, other: "CalendarEvent") -> bool:
        """Check if this event overlaps with another."""
        return self.start < other.end and other.start < self.end

    @property
    def duration(self) -> timedelta:
        return self.end - self.start


class CalendarManager:
    """In-memory calendar manager with full CRUD and scheduling utilities.

    Provides local storage with optional Google Calendar sync via the
    ``GoogleCalendarService`` adapter.
    """

    def __init__(self) -> None:
        self._events: Dict[str, CalendarEvent] = {}

    def get_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Return events within the specified date range (inclusive).

        Args:
            start_date: Start of range. Defaults to start of today.
            end_date: End of range. Defaults to end of today.
        """
        if start_date is None:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if end_date is None:
            end_date = start_date.replace(hour=23, minute=59, second=59)

        results: List[Dict[str, Any]] = []
        for event in self._events.values():
            if event.end >= start_date and event.start <= end_date:
                results.append(event.to_dict())

        results.sort(key=lambda e: e["start"])
        return results

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Return a single event by ID."""
        event = self._events.get(event_id)
        return event.to_dict() if event else None

    def create_event(
        self,
        title: str,
        start: datetime,
        end: datetime,
        description: str = "",
        location: str = "",
        attendees: Optional[List[str]] = None,
        all_day: bool = False,
        recurring: bool = False,
        recurrence_rule: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new calendar event.

        Args:
            title: Event title.
            start: Start datetime.
            end: End datetime.
            description: Optional description/notes.
            location: Optional location string.
            attendees: List of attendee email addresses.
            all_day: Whether this is an all-day event.
            recurring: Whether the event recurs.
            recurrence_rule: RRULE string for recurring events.
            metadata: Additional key-value metadata.

        Returns:
            The created event as a dictionary.

        Raises:
            ValueError: If end is before start or title is empty.
        """
        if not title.strip():
            raise ValueError("Event title cannot be empty")
        if end <= start:
            raise ValueError("Event end time must be after start time")

        event_id = str(uuid.uuid4())
        event = CalendarEvent(
            event_id=event_id,
            title=title.strip(),
            start=start,
            end=end,
            description=description,
            location=location,
            attendees=attendees or [],
            all_day=all_day,
            recurring=recurring,
            recurrence_rule=recurrence_rule,
            metadata=metadata or {},
        )

        self._events[event_id] = event
        logger.info("Created event '%s' (id=%s)", title, event_id)
        return event.to_dict()

    def update_event(self, event_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update fields of an existing event.

        Args:
            event_id: ID of the event to update.
            updates: Dict of field names and new values.

        Returns:
            Updated event dict, or None if not found.
        """
        event = self._events.get(event_id)
        if event is None:
            logger.warning("Event not found for update: %s", event_id)
            return None

        for key, value in updates.items():
            if key == "start" and isinstance(value, str):
                value = datetime.fromisoformat(value)
            elif key == "end" and isinstance(value, str):
                value = datetime.fromisoformat(value)
            if hasattr(event, key):
                setattr(event, key, value)

        logger.info("Updated event %s", event_id)
        return event.to_dict()

    def delete_event(self, event_id: str) -> bool:
        """Delete an event by ID. Returns True if the event existed."""
        if event_id in self._events:
            del self._events[event_id]
            logger.info("Deleted event %s", event_id)
            return True
        return False

    def get_today_events(self) -> List[Dict[str, Any]]:
        """Return all events scheduled for today."""
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59)
        return self.get_events(start, end)

    def get_week_events(self) -> List[Dict[str, Any]]:
        """Return all events for the current week (Monday-Sunday)."""
        now = datetime.now()
        monday = now - timedelta(days=now.weekday())
        start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        sunday = monday + timedelta(days=6)
        end = sunday.replace(hour=23, minute=59, second=59)
        return self.get_events(start, end)

    def check_conflicts(
        self, start: datetime, end: datetime, exclude_event_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find events that overlap with the given time slot.

        Args:
            start: Proposed start time.
            end: Proposed end time.
            exclude_event_id: Optional event ID to exclude (for rescheduling).

        Returns:
            List of conflicting event dicts.
        """
        conflicts: List[Dict[str, Any]] = []
        proposed = CalendarEvent(event_id="", title="", start=start, end=end)

        for event in self._events.values():
            if exclude_event_id and event.event_id == exclude_event_id:
                continue
            if proposed.overlaps(event):
                conflicts.append(event.to_dict())

        return conflicts

    def suggest_times(
        self,
        duration_minutes: int,
        date_range: Optional[str] = None,
        attendees: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Suggest available time slots that don't conflict with existing events.

        Args:
            duration_minutes: Required duration in minutes.
            date_range: Optional ISO date range (``"2024-01-01:2024-01-31"``).
            attendees: Optional list of attendees (placeholder for calendar integration).

        Returns:
            List of suggested time slot dicts with ``start`` and ``end`` keys.
        """
        now = datetime.now()
        if date_range and ":" in date_range:
            parts = date_range.split(":")
            range_start = datetime.fromisoformat(parts[0].strip())
            range_end = datetime.fromisoformat(parts[1].strip())
        else:
            range_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            range_end = range_start + timedelta(days=14)

        suggestions: List[Dict[str, Any]] = []
        current = range_start
        duration = timedelta(minutes=duration_minutes)
        slot_interval = timedelta(minutes=30)

        business_start = 9  # 9 AM
        business_end = 17  # 5 PM

        while current + duration <= range_end:
            # Only suggest during business hours on weekdays
            if current.weekday() < 5 and business_start <= current.hour < business_end:
                slot_end = current + duration
                conflicts = self.check_conflicts(current, slot_end)
                if not conflicts:
                    suggestions.append({
                        "start": current.isoformat(),
                        "end": slot_end.isoformat(),
                    })
                    if len(suggestions) >= 10:
                        break

            current += slot_interval
            # Skip to next day if past business hours
            if current.hour >= business_end:
                current = (current + timedelta(days=1)).replace(
                    hour=business_start, minute=0, second=0, microsecond=0
                )

        return suggestions

    def get_free_slots(
        self, date: datetime, business_hours_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Return free time slots for a given date.

        Args:
            date: The date to find free slots for.
            business_hours_only: Restrict to 9 AM - 5 PM.

        Returns:
            List of free slot dicts with ``start`` and ``end`` keys.
        """
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=23, minute=59, second=59)

        if business_hours_only:
            day_start = date.replace(hour=9, minute=0, second=0, microsecond=0)
            day_end = date.replace(hour=17, minute=0, second=0, microsecond=0)

        # Collect busy periods
        busy_periods: List[tuple] = []
        for event in self._events.values():
            if event.end >= day_start and event.start <= day_end:
                busy_start = max(event.start, day_start)
                busy_end = min(event.end, day_end)
                busy_periods.append((busy_start, busy_end))

        busy_periods.sort()

        # Merge overlapping busy periods
        merged: List[tuple] = []
        for start, end in busy_periods:
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        # Find free slots between busy periods
        free_slots: List[Dict[str, Any]] = []
        current = day_start

        for busy_start, busy_end in merged:
            if current < busy_start:
                free_slots.append({
                    "start": current.isoformat(),
                    "end": busy_start.isoformat(),
                })
            current = max(current, busy_end)

        if current < day_end:
            free_slots.append({
                "start": current.isoformat(),
                "end": day_end.isoformat(),
            })

        return free_slots

    def import_events(self, events: List[Dict[str, Any]]) -> int:
        """Bulk import events from a list of dicts. Returns count imported."""
        count = 0
        for data in events:
            try:
                event = CalendarEvent.from_dict(data)
                self._events[event.event_id] = event
                count += 1
            except Exception as exc:
                logger.warning("Failed to import event: %s", exc)
        return count

    def export_events(self) -> List[Dict[str, Any]]:
        """Export all events as a list of dicts."""
        return [e.to_dict() for e in self._events.values()]
