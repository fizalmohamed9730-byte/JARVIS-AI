"""
User Profile Management for JARVIS.

Builds and maintains user profiles from interactions, tracking
preferences, routines, app usage, contacts, and writing style.
"""

import json
import logging
import os
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    """Record of a single usage event."""
    timestamp: float
    category: str
    detail: str
    frequency: int = 1


@dataclass
class WritingStyleProfile:
    """Profile of the user's writing/speaking style."""
    avg_message_length: float = 0.0
    preferred_greetings: List[str] = field(default_factory=list)
    preferred_closings: List[str] = field(default_factory=list)
    common_phrases: List[str] = field(default_factory=list)
    formality_level: str = "casual"
    uses_emojis: bool = False
    uses_slang: bool = False
    total_messages_analyzed: int = 0


class UserProfile:
    """
    Manages and maintains a comprehensive user profile.

    Builds the profile from interactions over time, tracking preferences,
    routines, app usage, contacts, and communication style.
    """

    def __init__(self, profile_dir: Optional[str] = None):
        """
        Initialize the user profile manager.

        Args:
            profile_dir: Directory to persist profiles. Defaults to ~/.jarvis/profiles/.
        """
        self._profile_dir = profile_dir or str(Path.home() / ".jarvis" / "profiles")
        self._user_id: str = "default"
        self._preferences: Dict[str, Any] = {}
        self._routine_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._frequent_apps: Dict[str, UsageRecord] = {}
        self._frequent_contacts: Dict[str, UsageRecord] = {}
        self._writing_style = WritingStyleProfile()
        self._message_history: List[Dict[str, Any]] = []
        self._interaction_count: int = 0
        self._first_seen: float = time.time()
        self._last_seen: float = time.time()
        self._custom_data: Dict[str, Any] = {}

    @property
    def user_id(self) -> str:
        """Return the user ID."""
        return self._user_id

    @property
    def interaction_count(self) -> int:
        """Return the total interaction count."""
        return self._interaction_count

    async def initialize(self, user_id: str = "default") -> None:
        """
        Initialize the profile, loading from disk if available.

        Args:
            user_id: User identifier.
        """
        self._user_id = user_id
        await self._load_profile()

    async def _load_profile(self) -> None:
        """Load profile data from disk."""
        profile_path = self._get_profile_path()
        if os.path.exists(profile_path):
            try:
                loop = __import__("asyncio").get_event_loop()

                def _read():
                    with open(profile_path, "r", encoding="utf-8") as f:
                        return json.load(f)

                data = await loop.run_in_executor(None, _read)
                self._preferences = data.get("preferences", {})
                self._routine_patterns = defaultdict(list, data.get("routine_patterns", {}))
                self._interaction_count = data.get("interaction_count", 0)
                self._first_seen = data.get("first_seen", time.time())
                self._last_seen = data.get("last_seen", time.time())
                self._custom_data = data.get("custom_data", {})

                for key, val in data.get("frequent_apps", {}).items():
                    self._frequent_apps[key] = UsageRecord(**val)
                for key, val in data.get("frequent_contacts", {}).items():
                    self._frequent_contacts[key] = UsageRecord(**val)

                style_data = data.get("writing_style", {})
                self._writing_style = WritingStyleProfile(
                    avg_message_length=style_data.get("avg_message_length", 0.0),
                    preferred_greetings=style_data.get("preferred_greetings", []),
                    preferred_closings=style_data.get("preferred_closings", []),
                    common_phrases=style_data.get("common_phrases", []),
                    formality_level=style_data.get("formality_level", "casual"),
                    uses_emojis=style_data.get("uses_emojis", False),
                    uses_slang=style_data.get("uses_slang", False),
                    total_messages_analyzed=style_data.get("total_messages_analyzed", 0),
                )

                logger.info("Loaded profile for user '%s'", self._user_id)
            except Exception as e:
                logger.warning("Failed to load profile: %s", e)

    async def _save_profile(self) -> None:
        """Persist profile data to disk."""
        os.makedirs(self._profile_dir, exist_ok=True)
        profile_path = self._get_profile_path()

        data = {
            "user_id": self._user_id,
            "preferences": self._preferences,
            "routine_patterns": dict(self._routine_patterns),
            "frequent_apps": {
                k: {
                    "timestamp": r.timestamp,
                    "category": r.category,
                    "detail": r.detail,
                    "frequency": r.frequency,
                }
                for k, r in self._frequent_apps.items()
            },
            "frequent_contacts": {
                k: {
                    "timestamp": r.timestamp,
                    "category": r.category,
                    "detail": r.detail,
                    "frequency": r.frequency,
                }
                for k, r in self._frequent_contacts.items()
            },
            "writing_style": {
                "avg_message_length": self._writing_style.avg_message_length,
                "preferred_greetings": self._writing_style.preferred_greetings,
                "preferred_closings": self._writing_style.preferred_closings,
                "common_phrases": self._writing_style.common_phrases,
                "formality_level": self._writing_style.formality_level,
                "uses_emojis": self._writing_style.uses_emojis,
                "uses_slang": self._writing_style.uses_slang,
                "total_messages_analyzed": self._writing_style.total_messages_analyzed,
            },
            "interaction_count": self._interaction_count,
            "first_seen": self._first_seen,
            "last_seen": self._last_seen,
            "custom_data": self._custom_data,
        }

        try:
            loop = __import__("asyncio").get_event_loop()

            def _write():
                with open(profile_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

            await loop.run_in_executor(None, _write)
            logger.debug("Profile saved for user '%s'", self._user_id)
        except Exception as e:
            logger.error("Failed to save profile: %s", e)

    def _get_profile_path(self) -> str:
        """Get the file path for this user's profile."""
        return os.path.join(self._profile_dir, f"{self._user_id}.json")

    def get_preferences(self) -> Dict[str, Any]:
        """
        Get all stored preferences.

        Returns:
            Dictionary of preference key-value pairs.
        """
        return dict(self._preferences)

    async def update_preference(self, key: str, value: Any) -> None:
        """
        Update or add a user preference.

        Args:
            key: Preference key (e.g. "theme", "language").
            value: Preference value.
        """
        old_value = self._preferences.get(key)
        self._preferences[key] = value
        self._last_seen = time.time()
        logger.info("Preference updated: %s = %s (was: %s)", key, value, old_value)
        await self._save_profile()

    async def remove_preference(self, key: str) -> bool:
        """
        Remove a user preference.

        Args:
            key: Preference key to remove.

        Returns:
            True if the preference existed and was removed.
        """
        if key in self._preferences:
            del self._preferences[key]
            await self._save_profile()
            return True
        return False

    def get_routine_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get detected routine patterns.

        Returns:
            Dictionary mapping pattern names to occurrence records.
        """
        return dict(self._routine_patterns)

    async def record_routine(
        self,
        pattern_name: str,
        action: str,
        time_of_day: Optional[str] = None,
    ) -> None:
        """
        Record a routine action for pattern detection.

        Args:
            pattern_name: Name of the routine (e.g. "morning").
            action: Action performed (e.g. "check_email").
            time_of_day: Optional time descriptor.
        """
        record = {
            "action": action,
            "time_of_day": time_of_day,
            "timestamp": time.time(),
        }
        self._routine_patterns[pattern_name].append(record)

        max_records = 100
        if len(self._routine_patterns[pattern_name]) > max_records:
            self._routine_patterns[pattern_name] = self._routine_patterns[pattern_name][-max_records:]

        await self._save_profile()

    def get_frequent_apps(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most frequently used applications.

        Args:
            top_n: Number of top apps to return.

        Returns:
            List of app usage records sorted by frequency.
        """
        sorted_apps = sorted(
            self._frequent_apps.values(),
            key=lambda r: r.frequency,
            reverse=True,
        )
        return [
            {
                "app": r.detail,
                "category": r.category,
                "frequency": r.frequency,
                "last_used": r.timestamp,
            }
            for r in sorted_apps[:top_n]
        ]

    async def record_app_usage(self, app_name: str, category: str = "unknown") -> None:
        """
        Record an application usage event.

        Args:
            app_name: Name or path of the application.
            category: Application category.
        """
        now = time.time()
        if app_name in self._frequent_apps:
            self._frequent_apps[app_name].frequency += 1
            self._frequent_apps[app_name].timestamp = now
        else:
            self._frequent_apps[app_name] = UsageRecord(
                timestamp=now,
                category=category,
                detail=app_name,
                frequency=1,
            )
        await self._save_profile()

    def get_frequent_contacts(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most frequently contacted people.

        Args:
            top_n: Number of top contacts to return.

        Returns:
            List of contact records sorted by frequency.
        """
        sorted_contacts = sorted(
            self._frequent_contacts.values(),
            key=lambda r: r.frequency,
            reverse=True,
        )
        return [
            {
                "name": r.detail,
                "category": r.category,
                "frequency": r.frequency,
                "last_contact": r.timestamp,
            }
            for r in sorted_contacts[:top_n]
        ]

    async def record_contact(self, contact_name: str, interaction_type: str = "message") -> None:
        """
        Record a contact interaction.

        Args:
            contact_name: Name of the contact.
            interaction_type: Type of interaction (message, call, email).
        """
        now = time.time()
        if contact_name in self._frequent_contacts:
            self._frequent_contacts[contact_name].frequency += 1
            self._frequent_contacts[contact_name].timestamp = now
        else:
            self._frequent_contacts[contact_name] = UsageRecord(
                timestamp=now,
                category=interaction_type,
                detail=contact_name,
                frequency=1,
            )
        await self._save_profile()

    def get_writing_style(self) -> WritingStyleProfile:
        """
        Get the user's writing/speaking style profile.

        Returns:
            WritingStyleProfile object.
        """
        return self._writing_style

    async def analyze_writing_style(self, messages: List[str]) -> None:
        """
        Analyze a batch of messages to update the writing style profile.

        Args:
            messages: List of user message strings.
        """
        if not messages:
            return

        import re

        total_length = 0
        greetings = Counter()
        closings = Counter()
        phrases = Counter()
        emoji_count = 0
        slang_indicators = 0

        slang_words = {
            "lol", "omg", "btw", "imo", "tbh", "ngl", "fr", "smh", "fml",
            "bruh", "lowkey", "highkey", "vibe", "slay", "no cap", "bet",
        }

        greeting_patterns = [
            r"^(hi|hello|hey|yo|sup|howdy|greetings|what'?s up)\b",
        ]
        closing_patterns = [
            r"\b(thanks|thank you|bye|see you|later|cheers|peace|good night)\s*[!.]*$",
        ]

        for msg in messages:
            total_length += len(msg)
            msg_lower = msg.lower().strip()

            for pattern in greeting_patterns:
                match = re.match(pattern, msg_lower)
                if match:
                    greetings[match.group(1)] += 1

            for pattern in closing_patterns:
                match = re.search(pattern, msg_lower)
                if match:
                    closings[match.group(1)] += 1

            words = msg_lower.split()
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                if len(bigram) > 5:
                    phrases[bigram] += 1

            if re.search(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF]', msg):
                emoji_count += 1

            for word in words:
                if word in slang_words:
                    slang_indicators += 1

        n = len(messages)
        style = self._writing_style
        style.avg_message_length = (style.avg_message_length * style.total_messages_analyzed + total_length) / max(n + style.total_messages_analyzed, 1)
        style.total_messages_analyzed += n

        style.preferred_greetings = [g for g, _ in greetings.most_common(5)]
        style.preferred_closings = [c for c, _ in closings.most_common(5)]
        style.common_phrases = [p for p, _ in phrases.most_common(10)]
        style.uses_emojis = emoji_count > n * 0.1
        style.uses_slang = slang_indicators > n * 0.05

        if style.avg_message_length < 30:
            style.formality_level = "very_casual"
        elif style.avg_message_length < 80:
            style.formality_level = "casual"
        elif style.avg_message_length < 150:
            style.formality_level = "moderate"
        else:
            style.formality_level = "formal"

        await self._save_profile()
        logger.info("Writing style analyzed from %d messages", n)

    async def record_interaction(self, message: str) -> None:
        """
        Record a user interaction for profile building.

        Args:
            message: User message text.
        """
        self._interaction_count += 1
        self._last_seen = time.time()

        self._message_history.append({
            "text": message,
            "timestamp": time.time(),
        })
        max_history = 200
        if len(self._message_history) > max_history:
            self._message_history = self._message_history[-max_history:]

        if self._interaction_count % 10 == 0:
            messages = [m["text"] for m in self._message_history]
            await self.analyze_writing_style(messages)

    async def export_profile(self, filepath: str) -> None:
        """
        Export the full profile to a JSON file.

        Args:
            filepath: Path to write the exported profile.
        """
        data = {
            "user_id": self._user_id,
            "preferences": self._preferences,
            "routine_patterns": dict(self._routine_patterns),
            "frequent_apps": self.get_frequent_apps(100),
            "frequent_contacts": self.get_frequent_contacts(100),
            "writing_style": {
                "avg_message_length": self._writing_style.avg_message_length,
                "preferred_greetings": self._writing_style.preferred_greetings,
                "preferred_closings": self._writing_style.preferred_closings,
                "common_phrases": self._writing_style.common_phrases,
                "formality_level": self._writing_style.formality_level,
                "uses_emojis": self._writing_style.uses_emojis,
                "uses_slang": self._writing_style.uses_slang,
                "total_messages_analyzed": self._writing_style.total_messages_analyzed,
            },
            "interaction_count": self._interaction_count,
            "first_seen": self._first_seen,
            "last_seen": self._last_seen,
            "custom_data": self._custom_data,
            "exported_at": time.time(),
        }

        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        loop = __import__("asyncio").get_event_loop()

        def _write():
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        await loop.run_in_executor(None, _write)
        logger.info("Profile exported to %s", filepath)

    async def import_profile(self, filepath: str) -> bool:
        """
        Import a profile from a JSON file.

        Args:
            filepath: Path to the profile file.

        Returns:
            True if import was successful.
        """
        if not os.path.exists(filepath):
            logger.error("Profile file not found: %s", filepath)
            return False

        try:
            loop = __import__("asyncio").get_event_loop()

            def _read():
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)

            data = await loop.run_in_executor(None, _read)

            self._user_id = data.get("user_id", self._user_id)
            self._preferences = data.get("preferences", {})
            self._routine_patterns = defaultdict(list, data.get("routine_patterns", {}))
            self._interaction_count = data.get("interaction_count", 0)
            self._first_seen = data.get("first_seen", time.time())
            self._last_seen = data.get("last_seen", time.time())
            self._custom_data = data.get("custom_data", {})

            for app_data in data.get("frequent_apps", []):
                name = app_data.get("app", app_data.get("detail", ""))
                if name:
                    self._frequent_apps[name] = UsageRecord(
                        timestamp=app_data.get("last_used", app_data.get("timestamp", time.time())),
                        category=app_data.get("category", "unknown"),
                        detail=name,
                        frequency=app_data.get("frequency", 1),
                    )

            for contact_data in data.get("frequent_contacts", []):
                name = contact_data.get("name", contact_data.get("detail", ""))
                if name:
                    self._frequent_contacts[name] = UsageRecord(
                        timestamp=contact_data.get("last_contact", contact_data.get("timestamp", time.time())),
                        category=contact_data.get("category", "unknown"),
                        detail=name,
                        frequency=contact_data.get("frequency", 1),
                    )

            await self._save_profile()
            logger.info("Profile imported from %s for user '%s'", filepath, self._user_id)
            return True

        except Exception as e:
            logger.error("Profile import failed: %s", e)
            return False

    def get_profile_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the user profile.

        Returns:
            Dictionary with profile summary data.
        """
        return {
            "user_id": self._user_id,
            "interaction_count": self._interaction_count,
            "first_seen": self._first_seen,
            "last_seen": self._last_seen,
            "preferences": self._preferences,
            "top_apps": self.get_frequent_apps(5),
            "top_contacts": self.get_frequent_contacts(5),
            "writing_style": {
                "formality": self._writing_style.formality_level,
                "avg_length": round(self._writing_style.avg_message_length, 1),
                "uses_emojis": self._writing_style.uses_emojis,
                "uses_slang": self._writing_style.uses_slang,
            },
            "routine_patterns": list(self._routine_patterns.keys()),
        }
