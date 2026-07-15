"""Smart scheduling with meeting optimization and pattern detection."""

import logging
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

try:
    import pytz
except ImportError:
    pytz = None  # type: ignore[assignment]


class SmartScheduler:
    """Intelligent scheduling that finds optimal meeting times, detects patterns,
    and generates meeting agendas and summaries.
    """

    # Common meeting location suggestions based on context
    _LOCATION_SUGGESTIONS = {
        "interview": ["Conference Room A", "Video Call (Zoom)", "Video Call (Teams)"],
        "standup": ["Daily Standup Area", "Video Call (Quick Huddle)"],
        "review": ["Board Room", "Video Call (Zoom)"],
        "one-on-one": ["Manager Office", "Private Meeting Room", "Video Call"],
        "workshop": ["Training Room", "Large Conference Room"],
        "brainstorm": ["Whiteboard Room", "Creative Space"],
        "default": ["Conference Room", "Video Call", "Breakout Room"],
    }

    def find_best_time(
        self,
        duration_minutes: int,
        participants: List[str],
        preferred_times: Optional[List[str]] = None,
        existing_events: Optional[List[Dict[str, Any]]] = None,
        timezone_name: str = "UTC",
    ) -> Dict[str, Any]:
        """Find the best meeting time considering participant availability.

        Args:
            duration_minutes: Required meeting duration.
            participants: List of participant identifiers.
            preferred_times: Optional list of preferred ISO time strings.
            existing_events: Events to check for conflicts.
            timezone_name: IANA timezone name.

        Returns:
            Dict with ``best_time``, ``alternatives``, and ``score``.
        """
        tz = self._get_timezone(timezone_name)
        now = datetime.now(tz)
        duration = timedelta(minutes=duration_minutes)

        existing_events = existing_events or []
        conflicts = []
        for evt in existing_events:
            start = evt.get("start", "")
            end = evt.get("end", "")
            if isinstance(start, str) and start:
                try:
                    start_dt = datetime.fromisoformat(start)
                    end_dt = datetime.fromisoformat(end)
                    conflicts.append((start_dt, end_dt))
                except ValueError:
                    pass

        # Generate candidate slots for the next 14 business days
        candidates: List[Dict[str, Any]] = []
        current = now
        search_end = now + timedelta(days=14)

        while current < search_end:
            if current.weekday() < 5:  # Weekdays only
                for hour in range(9, 17):  # Business hours
                    slot_start = current.replace(hour=hour, minute=0, second=0, microsecond=0)
                    slot_end = slot_start + duration

                    if slot_end.hour > 17:
                        continue
                    if slot_start <= now:
                        continue

                    # Check conflicts
                    has_conflict = False
                    for c_start, c_end in conflicts:
                        if slot_start < c_end and c_start < slot_end:
                            has_conflict = True
                            break

                    if not has_conflict:
                        # Score this slot
                        score = self._score_time_slot(slot_start, preferred_times, participants)

                        candidates.append({
                            "start": slot_start.isoformat(),
                            "end": slot_end.isoformat(),
                            "score": score,
                        })

            current += timedelta(days=1)

        # Sort by score (highest first)
        candidates.sort(key=lambda x: x["score"], reverse=True)

        best = candidates[0] if candidates else None
        alternatives = candidates[1:5]

        return {
            "best_time": best,
            "alternatives": alternatives,
            "total_slots_checked": len(candidates),
            "participants": participants,
            "duration_minutes": duration_minutes,
        }

    def _score_time_slot(
        self,
        slot_start: datetime,
        preferred_times: Optional[List[str]],
        participants: List[str],
    ) -> float:
        """Score a time slot based on preferences and common patterns."""
        score = 50.0  # Base score

        # Prefer morning slots (slightly)
        if 9 <= slot_start.hour <= 11:
            score += 10
        elif slot_start.hour == 14:
            score += 5  # After lunch is decent
        elif slot_start.hour >= 16:
            score -= 10  # Late afternoon less preferred

        # Avoid Monday 9 AM (often busy with standups)
        if slot_start.weekday() == 0 and slot_start.hour == 9:
            score -= 5

        # Avoid Friday afternoon (people are winding down)
        if slot_start.weekday() == 4 and slot_start.hour >= 15:
            score -= 15

        # Check preferred times
        if preferred_times:
            for pref in preferred_times:
                try:
                    pref_dt = datetime.fromisoformat(pref)
                    hour_diff = abs(slot_start.hour - pref_dt.hour)
                    if hour_diff == 0:
                        score += 20
                    elif hour_diff <= 1:
                        score += 10
                except ValueError:
                    pass

        return score

    def suggest_meeting_location(self, participants: List[str], meeting_type: str = "default") -> List[str]:
        """Suggest appropriate meeting locations based on meeting type.

        Args:
            participants: List of participant identifiers.
            meeting_type: Type of meeting (interview, standup, review, etc.).

        Returns:
            List of suggested location strings.
        """
        meeting_type_lower = meeting_type.lower()
        locations = self._LOCATION_SUGGESTIONS.get(
            meeting_type_lower,
            self._LOCATION_SUGGESTIONS["default"],
        )

        # If many participants, suggest larger venues
        if len(participants) > 10:
            return ["Large Conference Room", "Auditorium", "Video Call (Zoom)"]
        elif len(participants) > 6:
            return ["Medium Conference Room", "Video Call (Zoom)", "Training Room"]

        return locations

    def detect_recurring_patterns(
        self, events: Sequence[Dict[str, Any]], min_occurrences: int = 3
    ) -> List[Dict[str, Any]]:
        """Detect recurring patterns in calendar events.

        Analyzes event titles and times to find patterns like weekly
        standups, monthly reviews, etc.

        Args:
            events: List of event dicts to analyze.
            min_occurrences: Minimum occurrences to consider a pattern.

        Returns:
            List of detected pattern dicts.
        """
        # Group events by normalized title
        title_groups: Dict[str, List[Dict[str, Any]]] = {}
        for event in events:
            title = self._normalize_title(event.get("title", ""))
            if title not in title_groups:
                title_groups[title] = []
            title_groups[title].append(event)

        patterns: List[Dict[str, Any]] = []
        for title, group in title_groups.items():
            if len(group) < min_occurrences:
                continue

            # Analyze day-of-week distribution
            day_counts = Counter()
            hour_counts = Counter()
            for evt in group:
                start = evt.get("start", "")
                if isinstance(start, str) and start:
                    try:
                        dt = datetime.fromisoformat(start)
                        day_counts[dt.strftime("%A")] += 1
                        hour_counts[dt.hour] += 1
                    except ValueError:
                        pass

            most_common_day = day_counts.most_common(1)[0] if day_counts else None
            most_common_hour = hour_counts.most_common(1)[0] if hour_counts else None

            pattern: Dict[str, Any] = {
                "title_pattern": title,
                "occurrences": len(group),
                "most_common_day": most_common_day[0] if most_common_day else None,
                "most_common_hour": most_common_hour[0] if most_common_hour else None,
                "sample_events": [e.get("title", "") for e in group[:3]],
            }

            # Determine frequency
            if len(group) >= 4:
                pattern["frequency"] = self._detect_frequency(group)

            patterns.append(pattern)

        patterns.sort(key=lambda p: p["occurrences"], reverse=True)
        return patterns

    def generate_meeting_agenda(
        self,
        topic: str,
        attendees: Optional[List[str]] = None,
        duration_minutes: int = 30,
        objectives: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate a structured meeting agenda.

        Args:
            topic: Meeting topic/purpose.
            attendees: List of attendee names or emails.
            duration_minutes: Total meeting duration.
            objectives: List of meeting objectives.

        Returns:
            Dict with ``title``, ``duration``, ``agenda_items``, and
            ``attendees`` keys.
        """
        attendees = attendees or []
        objectives = objectives or []

        # Build agenda items based on duration and objectives
        agenda_items: List[Dict[str, Any]] = []
        time_remaining = duration_minutes

        # Opening (always included, 2-5 min)
        opening_time = min(5, time_remaining // 5)
        agenda_items.append({
            "order": 1,
            "item": "Opening & Welcome",
            "duration_minutes": opening_time,
            "presenter": attendees[0] if attendees else "Host",
        })
        time_remaining -= opening_time

        # Objectives discussion
        if objectives:
            per_obj_time = time_remaining // (len(objectives) + 1)
            for i, obj in enumerate(objectives):
                agenda_items.append({
                    "order": len(agenda_items) + 1,
                    "item": obj,
                    "duration_minutes": per_obj_time,
                    "presenter": "Open",
                })
                time_remaining -= per_obj_time

        # Open discussion
        if time_remaining > 5:
            agenda_items.append({
                "order": len(agenda_items) + 1,
                "item": "Open Discussion / Q&A",
                "duration_minutes": time_remaining,
                "presenter": "All",
            })

        # Action items & closing (always at end)
        agenda_items.append({
            "order": len(agenda_items) + 1,
            "item": "Action Items & Next Steps",
            "duration_minutes": 3,
            "presenter": "Host",
        })

        return {
            "title": f"Meeting: {topic}",
            "duration_minutes": duration_minutes,
            "agenda_items": agenda_items,
            "attendees": attendees,
            "topic": topic,
        }

    def post_meeting_summary(
        self,
        event_title: str,
        attendees: Optional[List[str]] = None,
        notes: str = "",
        action_items: Optional[List[str]] = None,
        decisions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate a post-meeting summary document.

        Args:
            event_title: Title of the meeting.
            attendees: List of attendees.
            notes: Meeting notes / minutes.
            action_items: List of action items to track.
            decisions: Key decisions made during the meeting.

        Returns:
            Structured summary dict ready for export.
        """
        attendees = attendees or []
        action_items = action_items or []
        decisions = decisions or []

        now = datetime.now()

        summary = {
            "title": f"Meeting Summary: {event_title}",
            "date": now.strftime("%Y-%m-%d"),
            "generated_at": now.isoformat(),
            "attendees": attendees,
            "notes": notes,
            "action_items": [],
            "decisions": decisions,
        }

        for i, item in enumerate(action_items, 1):
            summary["action_items"].append({
                "id": i,
                "description": item,
                "status": "pending",
                "assigned_to": "TBD",
            })

        return summary

    def format_agenda_text(self, agenda: Dict[str, Any]) -> str:
        """Format an agenda dict into readable text."""
        lines: List[str] = []
        lines.append(f"{'='*60}")
        lines.append(f"  {agenda['title']}")
        lines.append(f"  Duration: {agenda['duration_minutes']} minutes")
        lines.append(f"{'='*60}")
        lines.append("")

        if agenda.get("attendees"):
            lines.append("Attendees:")
            for att in agenda["attendees"]:
                lines.append(f"  - {att}")
            lines.append("")

        lines.append("Agenda:")
        lines.append("-" * 40)
        cumulative = 0
        for item in agenda.get("agenda_items", []):
            cumulative += item["duration_minutes"]
            lines.append(
                f"  [{item['duration_minutes']:>3} min]  "
                f"({item.get('presenter', 'TBD'):>12})  "
                f"{item['item']}"
            )
        lines.append("-" * 40)
        lines.append(f"  Total: {agenda['duration_minutes']} minutes")
        lines.append(f"{'='*60}")

        return "\n".join(lines)

    def format_summary_text(self, summary: Dict[str, Any]) -> str:
        """Format a summary dict into readable text."""
        lines: List[str] = []
        lines.append(f"{'='*60}")
        lines.append(f"  {summary['title']}")
        lines.append(f"  Date: {summary['date']}")
        lines.append(f"{'='*60}")
        lines.append("")

        if summary.get("attendees"):
            lines.append("Attendees:")
            for att in summary["attendees"]:
                lines.append(f"  - {att}")
            lines.append("")

        if summary.get("decisions"):
            lines.append("Key Decisions:")
            for decision in summary["decisions"]:
                lines.append(f"  * {decision}")
            lines.append("")

        if summary.get("action_items"):
            lines.append("Action Items:")
            for item in summary["action_items"]:
                lines.append(f"  [{item['status'].upper()}] #{item['id']}: {item['description']}")
                if item.get("assigned_to") and item["assigned_to"] != "TBD":
                    lines.append(f"           Assigned to: {item['assigned_to']}")
            lines.append("")

        if summary.get("notes"):
            lines.append("Notes:")
            lines.append(summary["notes"])

        lines.append(f"{'='*60}")
        return "\n".join(lines)

    # --------------------------------------------------------------------- #
    # Helpers
    # --------------------------------------------------------------------- #

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalize an event title for pattern matching."""
        title = title.lower().strip()
        # Remove common prefixes/suffixes
        for prefix in ["re: ", "fwd: ", "[", "(", "#"]:
            title = title.replace(prefix, "")
        for suffix in ["]", ")", ".", ","]:
            title = title.replace(suffix, "")
        # Remove extra whitespace
        title = " ".join(title.split())
        return title

    @staticmethod
    def _detect_frequency(events: List[Dict[str, Any]]) -> str:
        """Detect the frequency of recurring events."""
        if len(events) < 2:
            return "unknown"

        dates: List[datetime] = []
        for evt in events:
            start = evt.get("start", "")
            if isinstance(start, str) and start:
                try:
                    dates.append(datetime.fromisoformat(start))
                except ValueError:
                    pass

        if len(dates) < 2:
            return "unknown"

        dates.sort()
        deltas = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
        avg_days = sum(deltas) / len(deltas)

        if avg_days <= 1:
            return "daily"
        elif 5 <= avg_days <= 9:
            return "weekly"
        elif 13 <= avg_days <= 16:
            return "bi-weekly"
        elif 27 <= avg_days <= 32:
            return "monthly"
        elif 85 <= avg_days <= 95:
            return "quarterly"
        elif 360 <= avg_days <= 370:
            return "yearly"
        else:
            return f"every {int(avg_days)} days"

    @staticmethod
    def _get_timezone(timezone_name: str):
        """Get a timezone object, defaulting to UTC if pytz is not available."""
        if pytz:
            return pytz.timezone(timezone_name)
        return timezone.utc
