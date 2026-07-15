"""Calendar tools for JARVIS AI agent system."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_CALENDAR_DIR = Path.home() / ".jarvis" / "calendar"
_CALENDAR_DIR.mkdir(parents=True, exist_ok=True)
_CALENDAR_FILE = _CALENDAR_DIR / "events.json"


def _load_events() -> list[dict[str, Any]]:
    """Load events from local storage."""
    if _CALENDAR_FILE.exists():
        try:
            with open(_CALENDAR_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save_events(events: list[dict[str, Any]]) -> None:
    """Save events to local storage."""
    try:
        with open(_CALENDAR_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2, default=str)
    except OSError as e:
        logger.error("Failed to save calendar: %s", e)


def _generate_event_id() -> str:
    """Generate a unique event ID."""
    return f"evt_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"


def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse a date string in various formats."""
    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %I:%M %p",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
        "%B %d, %Y %H:%M",
        "%B %d, %Y",
        "%b %d, %Y %H:%M",
        "%b %d, %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


@tool
def get_events(date_range: str = "today") -> str:
    """Get events within a date range.

    Args:
        date_range: Date range specification:
            - 'today': Today's events
            - 'tomorrow': Tomorrow's events
            - 'week': This week's events
            - 'month': This month's events
            - 'YYYY-MM-DD:YYYY-MM-DD': Custom range

    Returns:
        A formatted list of events in the specified range.
    """
    events = _load_events()
    now = datetime.now()

    if date_range.lower() == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif date_range.lower() == "tomorrow":
        start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif date_range.lower() == "week":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start -= timedelta(days=start.weekday())
        end = start + timedelta(days=7)
    elif date_range.lower() == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
    elif ":" in date_range:
        parts = date_range.split(":")
        start = _parse_date(parts[0].strip())
        end = _parse_date(parts[1].strip())
        if not start or not end:
            return "Error: Invalid date range format. Use 'YYYY-MM-DD:YYYY-MM-DD'."
    else:
        return (
            "Error: Invalid date_range. Use 'today', 'tomorrow', 'week', 'month', "
            "or 'YYYY-MM-DD:YYYY-MM-DD'."
        )

    filtered: list[dict[str, Any]] = []
    for evt in events:
        evt_start = _parse_date(evt.get("start", ""))
        if evt_start and start <= evt_start < end:
            filtered.append(evt)

    filtered.sort(key=lambda e: e.get("start", ""))

    if not filtered:
        return f"No events found for {date_range}."

    lines: list[str] = [f"Events for {date_range}:\n"]
    for i, evt in enumerate(filtered, 1):
        lines.append(
            f"{i}. {evt.get('title', 'Untitled')}\n"
            f"   Start: {evt.get('start', 'Unknown')}\n"
            f"   End: {evt.get('end', 'Unknown')}\n"
            + (f"   Description: {evt.get('description', '')}\n" if evt.get("description") else "")
            + (f"   Attendees: {', '.join(evt.get('attendees', []))}\n" if evt.get("attendees") else "")
            + f"   ID: {evt.get('id', 'N/A')}\n"
        )

    return "\n".join(lines)


@tool
def create_event(
    title: str,
    start: str,
    end: str = "",
    description: str = "",
    attendees: str = "",
) -> str:
    """Create a new calendar event.

    Args:
        title: Event title/name.
        start: Event start date/time (e.g., '2025-01-15 10:00').
        end: Event end date/time. If empty, defaults to 1 hour after start.
        description: Event description. Defaults to empty.
        attendees: Comma-separated list of attendee emails/names. Defaults to empty.

    Returns:
        A confirmation message with the event details.
    """
    if not title or not title.strip():
        return "Error: Event title is required."
    if not start or not start.strip():
        return "Error: Event start time is required."

    start_dt = _parse_date(start)
    if not start_dt:
        return f"Error: Could not parse start date '{start}'. Use format: YYYY-MM-DD HH:MM"

    if end and end.strip():
        end_dt = _parse_date(end)
        if not end_dt:
            return f"Error: Could not parse end date '{end}'. Use format: YYYY-MM-DD HH:MM"
    else:
        end_dt = start_dt + timedelta(hours=1)

    if end_dt <= start_dt:
        return "Error: End time must be after start time."

    attendee_list = [a.strip() for a in attendees.split(",") if a.strip()] if attendees else []

    event = {
        "id": _generate_event_id(),
        "title": title.strip(),
        "start": start_dt.strftime("%Y-%m-%d %H:%M"),
        "end": end_dt.strftime("%Y-%m-%d %H:%M"),
        "description": description.strip(),
        "attendees": attendee_list,
        "created": datetime.now().isoformat(),
    }

    events = _load_events()
    events.append(event)
    _save_events(events)

    return (
        f"Event created successfully:\n"
        f"  Title: {event['title']}\n"
        f"  Start: {event['start']}\n"
        f"  End: {event['end']}\n"
        f"  ID: {event['id']}"
    )


@tool
def update_event(event_id: str, updates: str) -> str:
    """Update an existing event.

    Args:
        event_id: The ID of the event to update.
        updates: JSON string of fields to update (e.g., '{"title": "New Title"}').
            Supported fields: title, start, end, description, attendees.

    Returns:
        A confirmation of the update.
    """
    if not event_id or not event_id.strip():
        return "Error: Event ID is required."

    try:
        update_data = json.loads(updates) if isinstance(updates, str) else updates
    except json.JSONDecodeError:
        return "Error: Invalid JSON in updates. Example: '{\"title\": \"New Title\"}'"

    events = _load_events()
    for evt in events:
        if evt.get("id") == event_id:
            if "title" in update_data:
                evt["title"] = update_data["title"]
            if "start" in update_data:
                dt = _parse_date(str(update_data["start"]))
                if dt:
                    evt["start"] = dt.strftime("%Y-%m-%d %H:%M")
            if "end" in update_data:
                dt = _parse_date(str(update_data["end"]))
                if dt:
                    evt["end"] = dt.strftime("%Y-%m-%d %H:%M")
            if "description" in update_data:
                evt["description"] = str(update_data["description"])
            if "attendees" in update_data:
                att = update_data["attendees"]
                if isinstance(att, str):
                    evt["attendees"] = [a.strip() for a in att.split(",") if a.strip()]
                elif isinstance(att, list):
                    evt["attendees"] = att

            _save_events(events)
            return f"Event '{event_id}' updated: {json.dumps({k: v for k, v in evt.items() if k != 'created'}, indent=2)}"

    return f"Error: Event with ID '{event_id}' not found."


@tool
def delete_event(event_id: str) -> str:
    """Delete a calendar event.

    Args:
        event_id: The ID of the event to delete.

    Returns:
        A confirmation of deletion.
    """
    if not event_id or not event_id.strip():
        return "Error: Event ID is required."

    events = _load_events()
    original_len = len(events)
    events = [e for e in events if e.get("id") != event_id]

    if len(events) == original_len:
        return f"Error: Event with ID '{event_id}' not found."

    _save_events(events)
    return f"Event '{event_id}' deleted successfully."


@tool
def check_conflicts(date_range: str = "week") -> str:
    """Check for scheduling conflicts within a date range.

    Args:
        date_range: Date range to check. Same format as get_events.

    Returns:
        A list of conflicting events or a message indicating no conflicts.
    """
    events = _load_events()
    now = datetime.now()

    if date_range.lower() == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif date_range.lower() == "week":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start -= timedelta(days=start.weekday())
        end = start + timedelta(days=7)
    elif ":" in date_range:
        parts = date_range.split(":")
        start = _parse_date(parts[0].strip())
        end = _parse_date(parts[1].strip())
        if not start or not end:
            return "Error: Invalid date range."
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)

    filtered: list[dict[str, Any]] = []
    for evt in events:
        evt_start = _parse_date(evt.get("start", ""))
        if evt_start and start <= evt_start < end:
            filtered.append(evt)

    conflicts: list[str] = []
    for i in range(len(filtered)):
        for j in range(i + 1, len(filtered)):
            a_start = _parse_date(filtered[i].get("start", ""))
            a_end = _parse_date(filtered[i].get("end", ""))
            b_start = _parse_date(filtered[j].get("start", ""))
            b_end = _parse_date(filtered[j].get("end", ""))

            if all([a_start, a_end, b_start, b_end]):
                if a_start < b_end and b_start < a_end:
                    conflicts.append(
                        f"  - '{filtered[i].get('title')}' ({filtered[i].get('start')} - {filtered[i].get('end')})\n"
                        f"    OVERLAPS WITH\n"
                        f"    '{filtered[j].get('title')}' ({filtered[j].get('start')} - {filtered[j].get('end')})"
                    )

    if not conflicts:
        return f"No scheduling conflicts found for {date_range}."

    return f"Found {len(conflicts)} conflict(s):\n\n" + "\n\n".join(conflicts)


@tool
def suggest_meeting_time(duration: str = "60", participants: str = "") -> str:
    """Suggest available meeting times based on existing events.

    Args:
        duration: Meeting duration in minutes. Defaults to 60.
        participants: Comma-separated list of participant names (for future integration).

    Returns:
        Suggested time slots for the meeting.
    """
    try:
        dur_minutes = int(duration)
    except ValueError:
        dur_minutes = 60

    events = _load_events()
    now = datetime.now()

    work_start_hour = 9
    work_end_hour = 17
    suggestions: list[str] = []

    for day_offset in range(1, 8):
        check_date = now + timedelta(days=day_offset)
        if check_date.weekday() >= 5:
            continue

        day_start = check_date.replace(hour=work_start_hour, minute=0, second=0, microsecond=0)
        day_end = check_date.replace(hour=work_end_hour, minute=0, second=0, microsecond=0)

        busy_slots: list[tuple[datetime, datetime]] = []
        for evt in events:
            evt_start = _parse_date(evt.get("start", ""))
            evt_end = _parse_date(evt.get("end", ""))
            if evt_start and evt_end:
                if evt_start.date() == check_date.date():
                    busy_slots.append((evt_start, evt_end))

        busy_slots.sort(key=lambda x: x[0])

        current = day_start
        while current + timedelta(minutes=dur_minutes) <= day_end:
            slot_end = current + timedelta(minutes=dur_minutes)
            conflict = False
            for busy_start, busy_end in busy_slots:
                if current < busy_end and slot_end > busy_start:
                    conflict = True
                    current = busy_end
                    break

            if not conflict:
                suggestions.append(
                    f"  {check_date.strftime('%A, %B %d')} at "
                    f"{current.strftime('%I:%M %p')} - {slot_end.strftime('%I:%M %p')}"
                )
                current = slot_end
                if len(suggestions) >= 5:
                    break
            else:
                continue

        if len(suggestions) >= 5:
            break

    if not suggestions:
        return "No available time slots found in the next 7 days."

    part_str = f" for {participants}" if participants else ""
    return f"Suggested meeting times ({dur_minutes} min){part_str}:\n\n" + "\n".join(suggestions)


calendar_tools = [get_events, create_event, update_event, delete_event, check_conflicts, suggest_meeting_time]
