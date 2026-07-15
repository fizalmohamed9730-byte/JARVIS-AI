"""Background reminder system using APScheduler with notification support."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    _HAS_APSCHEDULER = True
except ImportError:
    _HAS_APSCHEDULER = False
    logger.warning("APScheduler not installed. Install with: pip install apscheduler")


class Reminder:
    """Represents a single scheduled reminder."""

    def __init__(
        self,
        reminder_id: str,
        title: str,
        trigger_time: datetime,
        message: str = "",
        recurring: bool = False,
        recurrence_rule: str = "",
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.reminder_id = reminder_id
        self.title = title
        self.trigger_time = trigger_time
        self.message = message
        self.recurring = recurring
        self.recurrence_rule = recurrence_rule
        self.priority = priority
        self.metadata = metadata or {}
        self.snoozed_until: Optional[datetime] = None
        self.dismissed = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reminder_id": self.reminder_id,
            "title": self.title,
            "trigger_time": self.trigger_time.isoformat(),
            "message": self.message,
            "recurring": self.recurring,
            "recurrence_rule": self.recurrence_rule,
            "priority": self.priority,
            "metadata": self.metadata,
            "snoozed_until": self.snoozed_until.isoformat() if self.snoozed_until else None,
            "dismissed": self.dismissed,
        }


class ReminderSystem:
    """Manages scheduled reminders with background execution and notifications.

    Uses APScheduler for reliable background scheduling. Supports one-time,
    recurring, and snoozed reminders. Fires callbacks when reminders trigger.
    """

    def __init__(self, notification_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        """Initialize the reminder system.

        Args:
            notification_callback: Optional function called when a reminder fires.
                Receives the reminder dict as its argument.
        """
        self._reminders: Dict[str, Reminder] = {}
        self._notification_callback = notification_callback
        self._scheduler: Any = None
        self._started = False

        if _HAS_APSCHEDULER:
            self._scheduler = BackgroundScheduler(
                job_defaults={
                    "coalesce": True,
                    "max_instances": 1,
                    "misfire_grace_time": 60,
                }
            )
        else:
            logger.warning("ReminderSystem running without APScheduler - background scheduling disabled")

    def start(self) -> None:
        """Start the background scheduler."""
        if self._scheduler and not self._started:
            try:
                self._scheduler.start()
                self._started = True
                logger.info("Reminder scheduler started")
            except Exception as exc:
                logger.exception("Failed to start reminder scheduler: %s", exc)

    def stop(self) -> None:
        """Stop the background scheduler gracefully."""
        if self._scheduler and self._started:
            try:
                self._scheduler.shutdown(wait=False)
                self._started = False
                logger.info("Reminder scheduler stopped")
            except Exception as exc:
                logger.warning("Error stopping scheduler: %s", exc)

    def schedule_reminder(
        self,
        title: str,
        trigger_time: datetime,
        message: str = "",
        recurring: bool = False,
        recurrence_rule: str = "",
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Schedule a new reminder.

        Args:
            title: Reminder title.
            trigger_time: When to fire the reminder.
            message: Optional message body.
            recurring: Whether the reminder repeats.
            recurrence_rule: Cron-style rule for recurring reminders
                (e.g., ``"daily 9:00"`` or ``"weekly monday 10:00"``).
            priority: Priority level (higher = more important).
            metadata: Additional key-value data.

        Returns:
            The scheduled reminder as a dict.
        """
        reminder_id = str(uuid.uuid4())
        reminder = Reminder(
            reminder_id=reminder_id,
            title=title,
            trigger_time=trigger_time,
            message=message,
            recurring=recurring,
            recurrence_rule=recurrence_rule,
            priority=priority,
            metadata=metadata or {},
        )

        self._reminders[reminder_id] = reminder

        if self._scheduler and self._started:
            self._add_scheduler_job(reminder)
        else:
            logger.warning("Scheduler not running - reminder stored but not scheduled: %s", reminder_id)

        logger.info("Scheduled reminder '%s' (id=%s) for %s", title, reminder_id, trigger_time.isoformat())
        return reminder.to_dict()

    def cancel_reminder(self, reminder_id: str) -> bool:
        """Cancel and remove a reminder."""
        if reminder_id not in self._reminders:
            return False

        if self._scheduler:
            try:
                self._scheduler.remove_job(reminder_id)
            except Exception:
                pass

        del self._reminders[reminder_id]
        logger.info("Cancelled reminder %s", reminder_id)
        return True

    def snooze_reminder(self, reminder_id: str, minutes: int = 10) -> Dict[str, Any]:
        """Snooze a reminder for the specified number of minutes.

        Args:
            reminder_id: ID of the reminder to snooze.
            minutes: Minutes to snooze.

        Returns:
            Updated reminder dict, or error dict if not found.
        """
        reminder = self._reminders.get(reminder_id)
        if not reminder:
            return {"success": False, "error": f"Reminder not found: {reminder_id}"}

        new_time = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        reminder.snoozed_until = new_time
        reminder.trigger_time = new_time

        # Reschedule
        if self._scheduler:
            try:
                self._scheduler.remove_job(reminder_id)
            except Exception:
                pass
            self._add_scheduler_job(reminder)

        logger.info("Snoozed reminder %s for %d minutes", reminder_id, minutes)
        return reminder.to_dict()

    def check_reminders(self) -> List[Dict[str, Any]]:
        """Check for due reminders and return them.

        Returns:
            List of reminder dicts that are due (trigger_time <= now).
        """
        now = datetime.now(timezone.utc)
        due: List[Dict[str, Any]] = []

        for reminder in self._reminders.values():
            if reminder.dismissed:
                continue

            trigger_time = reminder.trigger_time
            if trigger_time.tzinfo is None:
                trigger_time = trigger_time.replace(tzinfo=timezone.utc)

            if trigger_time <= now:
                due.append(reminder.to_dict())
                self._fire_notification(reminder)

        return due

    def get_active_reminders(self) -> List[Dict[str, Any]]:
        """Return all non-dismissed, non-cancelled reminders."""
        now = datetime.now(timezone.utc)
        active: List[Dict[str, Any]] = []

        for reminder in self._reminders.values():
            if not reminder.dismissed:
                active.append(reminder.to_dict())

        active.sort(key=lambda r: r["trigger_time"])
        return active

    def dismiss_reminder(self, reminder_id: str) -> bool:
        """Mark a reminder as dismissed."""
        reminder = self._reminders.get(reminder_id)
        if not reminder:
            return False

        reminder.dismissed = True

        if self._scheduler:
            try:
                self._scheduler.remove_job(reminder_id)
            except Exception:
                pass

        logger.info("Dismissed reminder %s", reminder_id)
        return True

    def load_reminders(self, reminders: List[Dict[str, Any]]) -> int:
        """Load reminders from serialized data. Returns count loaded."""
        count = 0
        for data in reminders:
            try:
                trigger_time = data.get("trigger_time", "")
                if isinstance(trigger_time, str):
                    trigger_time = datetime.fromisoformat(trigger_time)

                reminder = Reminder(
                    reminder_id=data.get("reminder_id", str(uuid.uuid4())),
                    title=data.get("title", ""),
                    trigger_time=trigger_time,
                    message=data.get("message", ""),
                    recurring=data.get("recurring", False),
                    recurrence_rule=data.get("recurrence_rule", ""),
                    priority=data.get("priority", 0),
                    metadata=data.get("metadata", {}),
                )

                self._reminders[reminder.reminder_id] = reminder

                if self._scheduler and self._started and not reminder.dismissed:
                    self._add_scheduler_job(reminder)

                count += 1
            except Exception as exc:
                logger.warning("Failed to load reminder: %s", exc)

        return count

    def export_reminders(self) -> List[Dict[str, Any]]:
        """Export all active reminders as serialized dicts."""
        return [r.to_dict() for r in self._reminders.values() if not r.dismissed]

    # --------------------------------------------------------------------- #
    # Internal methods
    # --------------------------------------------------------------------- #

    def _add_scheduler_job(self, reminder: Reminder) -> None:
        """Add a reminder to the APScheduler."""
        if not self._scheduler:
            return

        def callback() -> None:
            self._fire_notification(reminder)

        try:
            trigger_time = reminder.trigger_time
            if trigger_time.tzinfo is None:
                trigger_time = trigger_time.replace(tzinfo=timezone.utc)

            if trigger_time <= datetime.now(timezone.utc):
                # Already due, fire immediately
                self._fire_notification(reminder)
                return

            if reminder.recurring and reminder.recurrence_rule:
                trigger = self._parse_recurrence(reminder.recurrence_rule)
                if trigger:
                    self._scheduler.add_job(
                        callback,
                        trigger=trigger,
                        id=reminder.reminder_id,
                        name=reminder.title,
                        replace_existing=True,
                    )
                    return

            self._scheduler.add_job(
                callback,
                trigger=DateTrigger(run_date=trigger_time),
                id=reminder.reminder_id,
                name=reminder.title,
                replace_existing=True,
            )
        except Exception as exc:
            logger.exception("Failed to schedule reminder %s: %s", reminder.reminder_id, exc)

    def _parse_recurrence(self, rule: str):
        """Parse a recurrence rule string into an APScheduler trigger."""
        rule_lower = rule.lower().strip()

        if "daily" in rule_lower or "every day" in rule_lower:
            return IntervalTrigger(days=1)
        elif "weekly" in rule_lower:
            return IntervalTrigger(weeks=1)
        elif "monthly" in rule_lower:
            return IntervalTrigger(months=1)
        elif "hourly" in rule_lower or "every hour" in rule_lower:
            return IntervalTrigger(hours=1)

        # Try cron format: "minute hour day month day_of_week"
        parts = rule_lower.split()
        if len(parts) >= 5:
            try:
                return CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                )
            except Exception:
                pass

        return None

    def _fire_notification(self, reminder: Reminder) -> None:
        """Trigger a notification for a fired reminder."""
        notification = {
            "type": "reminder",
            "reminder_id": reminder.reminder_id,
            "title": reminder.title,
            "message": reminder.message,
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "priority": reminder.priority,
            "metadata": reminder.metadata,
        }

        logger.info("Reminder fired: '%s' (id=%s)", reminder.title, reminder.reminder_id)

        if self._notification_callback:
            try:
                self._notification_callback(notification)
            except Exception as exc:
                logger.exception("Notification callback failed for reminder %s", reminder.reminder_id)
