"""Google Calendar integration via the Google Calendar API v3."""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarService:
    """Manages Google Calendar API interactions with OAuth2 and rate limiting.

    Handles authentication, event CRUD, sync, and retry logic for transient
    API errors.
    """

    def __init__(self) -> None:
        self._service: Any = None
        self._credentials: Any = None
        self._calendar_id: str = "primary"
        self._max_retries: int = 3
        self._retry_delay: float = 1.0

    def authenticate(
        self,
        credentials_path: str = "",
        token_path: str = "",
    ) -> Any:
        """Authenticate with Google Calendar using OAuth2 credentials.

        Args:
            credentials_path: Path to the OAuth2 client secrets JSON file.
                Defaults to ``credentials/google_calendar.json`` in the
                project root.
            token_path: Path to store the OAuth2 token. Defaults to
                ``credentials/token_calendar.json``.

        Returns:
            The authorized Google Calendar API service object.

        Raises:
            FileNotFoundError: If the credentials file does not exist.
            RuntimeError: If authentication fails.
        """
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
        except ImportError:
            raise RuntimeError(
                "Google API client libraries required. Install with:\n"
                "pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )

        if not credentials_path:
            base = os.path.dirname(os.path.abspath(__file__))
            credentials_path = os.path.join(base, "..", "credentials", "google_calendar.json")
        if not token_path:
            base = os.path.dirname(os.path.abspath(__file__))
            token_path = os.path.join(base, "..", "credentials", "token_calendar.json")

        creds = None

        # Load existing token
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, _SCOPES)

        # Refresh or obtain new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None

            if not creds:
                if not os.path.exists(credentials_path):
                    raise FileNotFoundError(
                        f"Google Calendar credentials not found: {credentials_path}\n"
                        "Download from Google Cloud Console > APIs > Credentials."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, _SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the token
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, "w") as f:
                f.write(creds.to_json())

        self._credentials = creds
        self._service = build("calendar", "v3", credentials=creds)
        logger.info("Google Calendar authenticated successfully")
        return self._service

    def _ensure_authenticated(self) -> None:
        if self._service is None:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

    def _execute_with_retry(self, request: Any) -> Any:
        """Execute an API request with exponential backoff retry."""
        import time

        last_error = None
        for attempt in range(self._max_retries):
            try:
                return request.execute()
            except Exception as exc:
                last_error = exc
                error_str = str(exc).lower()
                # Don't retry on client errors (4xx except 429)
                if "400" in error_str or "401" in error_str or "403" in error_str or "404" in error_str:
                    raise
                # Rate limit (429) or server error (5xx)
                if "429" in error_str or "500" in error_str or "503" in error_str:
                    delay = self._retry_delay * (2 ** attempt)
                    logger.warning("API rate limited or server error, retrying in %.1fs", delay)
                    time.sleep(delay)
                    continue
                raise

        raise RuntimeError(f"API request failed after {self._max_retries} retries: {last_error}")

    def sync_events(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Synchronize events from Google Calendar.

        Args:
            since: Only fetch events modified after this datetime.
                Defaults to 30 days ago.

        Returns:
            List of event dicts from Google Calendar.
        """
        self._ensure_authenticated()

        if since is None:
            from datetime import timedelta
            since = datetime.now(timezone.utc) - timedelta(days=30)

        time_min = since.isoformat() if since.tzinfo else since.replace(tzinfo=timezone.utc).isoformat()

        try:
            request = self._service.events().list(
                calendarId=self._calendar_id,
                timeMin=time_min,
                maxResults=250,
                singleEvents=True,
                orderBy="startTime",
            )
            result = self._execute_with_retry(request)
            events = result.get("items", [])
            logger.info("Synced %d events from Google Calendar", len(events))
            return [self._normalize_event(e) for e in events]
        except Exception as exc:
            logger.exception("Failed to sync Google Calendar events")
            raise RuntimeError(f"Sync failed: {exc}") from exc

    def create_event(self, event: Dict[str, Any]) -> str:
        """Create an event on Google Calendar.

        Args:
            event: Event dict with ``title``, ``start``, ``end``, and
                optional ``description``, ``location``, ``attendees`` keys.

        Returns:
            The Google event ID.
        """
        self._ensure_authenticated()

        body = {
            "summary": event.get("title", ""),
            "description": event.get("description", ""),
            "location": event.get("location", ""),
        }

        # Handle start/end times
        start_dt = event.get("start")
        end_dt = event.get("end")
        if isinstance(start_dt, str):
            start_dt = datetime.fromisoformat(start_dt)
        if isinstance(end_dt, str):
            end_dt = datetime.fromisoformat(end_dt)

        if event.get("all_day"):
            body["start"] = {"date": start_dt.strftime("%Y-%m-%d")}
            body["end"] = {"date": end_dt.strftime("%Y-%m-%d")}
        else:
            body["start"] = {"dateTime": start_dt.isoformat(), "timeZone": "UTC"}
            body["end"] = {"dateTime": end_dt.isoformat(), "timeZone": "UTC"}

        # Attendees
        attendees = event.get("attendees", [])
        if attendees:
            body["attendees"] = [{"email": addr} for addr in attendees]

        try:
            request = self._service.events().insert(
                calendarId=self._calendar_id,
                body=body,
            )
            result = self._execute_with_retry(request)
            event_id = result.get("id", "")
            logger.info("Created Google Calendar event: %s", event_id)
            return event_id
        except Exception as exc:
            logger.exception("Failed to create Google Calendar event")
            raise RuntimeError(f"Create failed: {exc}") from exc

    def update_event(self, google_event_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing Google Calendar event.

        Args:
            google_event_id: The Google event ID.
            updates: Fields to update.

        Returns:
            Updated event dict.
        """
        self._ensure_authenticated()

        body: Dict[str, Any] = {}
        if "title" in updates:
            body["summary"] = updates["title"]
        if "description" in updates:
            body["description"] = updates["description"]
        if "location" in updates:
            body["location"] = updates["location"]
        if "start" in updates:
            start = updates["start"]
            if isinstance(start, str):
                start = datetime.fromisoformat(start)
            body["start"] = {"dateTime": start.isoformat(), "timeZone": "UTC"}
        if "end" in updates:
            end = updates["end"]
            if isinstance(end, str):
                end = datetime.fromisoformat(end)
            body["end"] = {"dateTime": end.isoformat(), "timeZone": "UTC"}

        try:
            request = self._service.events().patch(
                calendarId=self._calendar_id,
                eventId=google_event_id,
                body=body,
            )
            result = self._execute_with_retry(request)
            logger.info("Updated Google Calendar event: %s", google_event_id)
            return self._normalize_event(result)
        except Exception as exc:
            logger.exception("Failed to update event %s", google_event_id)
            raise RuntimeError(f"Update failed: {exc}") from exc

    def delete_event(self, google_event_id: str) -> bool:
        """Delete a Google Calendar event."""
        self._ensure_authenticated()

        try:
            request = self._service.events().delete(
                calendarId=self._calendar_id,
                eventId=google_event_id,
            )
            self._execute_with_retry(request)
            logger.info("Deleted Google Calendar event: %s", google_event_id)
            return True
        except Exception as exc:
            logger.exception("Failed to delete event %s", google_event_id)
            return False

    def set_calendar_id(self, calendar_id: str) -> None:
        """Change the target calendar (default is 'primary')."""
        self._calendar_id = calendar_id

    @staticmethod
    def _normalize_event(google_event: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a Google Calendar event into a consistent dict format."""
        start = google_event.get("start", {})
        end = google_event.get("end", {})

        start_dt = start.get("dateTime") or start.get("date", "")
        end_dt = end.get("dateTime") or end.get("date", "")
        all_day = "date" in start and "dateTime" not in start

        attendees = [
            a.get("email", "") for a in google_event.get("attendees", [])
        ]

        return {
            "event_id": google_event.get("id", ""),
            "title": google_event.get("summary", ""),
            "start": start_dt,
            "end": end_dt,
            "description": google_event.get("description", ""),
            "location": google_event.get("location", ""),
            "attendees": attendees,
            "all_day": all_day,
            "html_link": google_event.get("htmlLink", ""),
            "status": google_event.get("status", ""),
            "creator": google_event.get("creator", {}).get("email", ""),
            "created": google_event.get("created", ""),
            "updated": google_event.get("updated", ""),
        }
