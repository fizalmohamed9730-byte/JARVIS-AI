"""Calendar system sub-package for event management and smart scheduling."""

from calendar_assistant.manager import CalendarManager
from calendar_assistant.google_calendar import GoogleCalendarService
from calendar_assistant.scheduler import SmartScheduler
from calendar_assistant.reminder import ReminderSystem

__all__ = [
    "CalendarManager",
    "GoogleCalendarService",
    "SmartScheduler",
    "ReminderSystem",
]
