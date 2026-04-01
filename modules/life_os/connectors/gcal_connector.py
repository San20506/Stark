"""
Google Calendar Connector
=========================
Reads events for the morning briefing.

Auth: OAuth2 user credentials (personal Gmail account).
First run will open a browser for authorization; subsequent runs use the
cached token file.

Required env vars:
  GCAL_CREDENTIALS_PATH   path to credentials.json from Google Cloud Console
  GCAL_TOKEN_PATH         path to token.json (auto-created after first auth)
  GCAL_CALENDAR_ID        calendar to read (default: "primary")
"""
import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

_SCOPES: list[str] = ["https://www.googleapis.com/auth/calendar.readonly"]


class GCalConnector:
    """Reads Google Calendar events for the life_os morning briefing."""

    def __init__(self) -> None:
        self._creds_path = os.environ.get(
            "GCAL_CREDENTIALS_PATH", "config/gcal_credentials.json"
        )
        self._token_path = os.environ.get(
            "GCAL_TOKEN_PATH", "config/gcal_token.json"
        )
        self._calendar_id = os.environ.get("GCAL_CALENDAR_ID", "primary")

    def get_events(
        self,
        target_date: date | None = None,
        days_ahead: int = 2,
    ) -> list[dict[str, Any]]:
        """
        Return events for ``target_date`` plus the next ``days_ahead`` days.

        Args:
            target_date: Date to start from (defaults to today).
            days_ahead: Number of additional days to include.

        Returns:
            List of event dicts with keys: summary, start, end, description.
            Returns empty list if credentials are not configured or fetch fails.
        """
        try:
            service = self._build_service()
        except Exception as exc:
            logger.warning("GCal service unavailable: %s", exc)
            return []

        start = target_date or date.today()
        end = start + timedelta(days=days_ahead)
        time_min = (
            datetime.combine(start, datetime.min.time())
            .replace(tzinfo=timezone.utc)
            .isoformat()
        )
        time_max = (
            datetime.combine(end, datetime.min.time())
            .replace(tzinfo=timezone.utc)
            .isoformat()
        )

        try:
            result = (
                service.events()
                .list(
                    calendarId=self._calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            return [self._parse_event(e) for e in result.get("items", [])]
        except Exception as exc:
            logger.error("GCal events fetch failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_service(self) -> Any:
        """Build and return the Google Calendar API service object."""
        # Lazy imports so the module loads without google-api packages installed.
        from google.auth.transport.requests import Request  # type: ignore
        from google.oauth2.credentials import Credentials  # type: ignore
        from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
        from googleapiclient.discovery import build  # type: ignore

        creds: Any = None
        if os.path.exists(self._token_path):
            creds = Credentials.from_authorized_user_file(self._token_path, _SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self._creds_path):
                    raise FileNotFoundError(
                        f"GCal credentials not found at {self._creds_path}. "
                        "Download from Google Cloud Console → APIs & Services → Credentials."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self._creds_path, _SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(self._token_path, "w", encoding="utf-8") as fh:
                fh.write(creds.to_json())

        return build("calendar", "v3", credentials=creds)

    @staticmethod
    def _parse_event(event: dict[str, Any]) -> dict[str, Any]:
        start_raw = event.get("start", {})
        end_raw = event.get("end", {})
        return {
            "summary": event.get("summary", "(no title)"),
            "start": start_raw.get("dateTime", start_raw.get("date", "")),
            "end": end_raw.get("dateTime", end_raw.get("date", "")),
            "description": event.get("description", ""),
        }
