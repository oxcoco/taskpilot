"""Google Calendar export integration for TaskPilot.

This module uses the Google Calendar REST API directly with standard-library
HTTP requests so it can be exercised in tests without adding a third-party
dependency.
"""

from __future__ import annotations

import datetime
import json
import os
from dataclasses import dataclass
from typing import Any, Iterable
from urllib import error, parse, request

from ..agents.deadline_parse import normalize_deadline
from ..database.models import Task, TaskStatus
from ..database.google_oauth import load_google_oauth_credentials

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"


@dataclass
class GoogleCalendarClient:
    """Minimal Google Calendar API client for exporting tasks."""

    calendar_id: str = "primary"
    timezone: str = "UTC"
    access_token: str | None = None
    refresh_token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    token_url: str = GOOGLE_TOKEN_URL
    api_base: str = GOOGLE_CALENDAR_API_BASE

    @classmethod
    def from_environment(
        cls,
        calendar_id: str | None = None,
        timezone: str | None = None,
    ) -> "GoogleCalendarClient":
        """Build a client from backend configuration or stored OAuth credentials.

        The preferred flow is stored Google OAuth refresh tokens saved during the
        Connect Google Calendar flow. Environment variables are only used for the
        backend client credentials and optional calendar defaults.
        """

        stored = load_google_oauth_credentials()
        return cls(
            calendar_id=calendar_id or os.getenv("GOOGLE_CALENDAR_ID", "primary"),
            timezone=timezone or os.getenv("GOOGLE_CALENDAR_TIMEZONE", "UTC"),
            access_token=os.getenv("GOOGLE_CALENDAR_ACCESS_TOKEN"),
            refresh_token=os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN") or (stored.refresh_token if stored else None),
            client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
        )

    @classmethod
    def from_connected_account(
        cls,
        calendar_id: str | None = None,
        timezone: str | None = None,
    ) -> "GoogleCalendarClient":
        stored = load_google_oauth_credentials()
        if not stored:
            raise RuntimeError("Google Calendar is not connected. Click Connect Google Calendar first.")
        return cls(
            calendar_id=calendar_id or os.getenv("GOOGLE_CALENDAR_ID", "primary"),
            timezone=timezone or os.getenv("GOOGLE_CALENDAR_TIMEZONE", "UTC"),
            refresh_token=stored.refresh_token,
            client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
        )

    def export_tasks(
        self,
        tasks: Iterable[Task],
        include_completed: bool = False,
        include_undated: bool = False,
    ) -> dict[str, Any]:
        """Export eligible tasks to Google Calendar.

        Tasks without a deadline are skipped by default so the export is
        predictable. Set ``include_undated`` to place them on today's date.
        """

        created: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []

        for task in tasks:
            if not include_completed and task.status == TaskStatus.COMPLETED:
                skipped.append({"id": task.id, "title": task.title, "reason": "completed"})
                continue

            event_date = self._resolve_event_date(task, include_undated=include_undated)
            if not event_date:
                skipped.append({"id": task.id, "title": task.title, "reason": "no deadline"})
                continue

            event = self._create_event_for_task(task, event_date)
            created.append(event)

        return {
            "calendar_id": self.calendar_id,
            "timezone": self.timezone,
            "exported_count": len(created),
            "skipped_count": len(skipped),
            "created_events": created,
            "skipped_tasks": skipped,
        }

    def _resolve_event_date(
        self,
        task: Task,
        *,
        include_undated: bool,
    ) -> datetime.date | None:
        if task.deadline:
            normalized = normalize_deadline(task.deadline)
            if not normalized:
                return None
            try:
                return datetime.date.fromisoformat(normalized)
            except ValueError:
                return None

        if include_undated:
            return datetime.date.today()

        return None

    def _create_event_for_task(self, task: Task, event_date: datetime.date) -> dict[str, Any]:
      payload = {
          "summary": task.title,
          "description": self._build_description(task),
          "start": {
              "date": event_date.isoformat(),
          },
          "end": {
              # Google Calendar all-day events use an exclusive end date.
              "date": (event_date + datetime.timedelta(days=1)).isoformat(),
          },
          "extendedProperties": {
              "private": {
                  "taskpilot_task_id": task.id,
              }
          },
      }

      return self._request_json(
          "POST",
          f"/calendars/{parse.quote(self.calendar_id, safe='')}/events",
          payload,
      )

    def _build_description(self, task: Task) -> str:
        parts = [f"TaskPilot task: {task.title}"]
        if task.description:
            parts.append(task.description)
        parts.append(f"Priority: {task.priority.value}")
        parts.append(f"Estimated hours: {task.estimated_hours}")
        parts.append(f"Task ID: {task.id}")
        return "\n".join(parts)

    def _resolve_access_token(self) -> str:
        if self.access_token:
            return self.access_token
        if not (self.refresh_token and self.client_id and self.client_secret):
            raise RuntimeError(
                "Google Calendar export requires GOOGLE_CALENDAR_ACCESS_TOKEN or a refresh token plus OAuth client credentials."
            )
        self.access_token = self._refresh_access_token()
        return self.access_token

    def _refresh_access_token(self) -> str:
        payload = parse.urlencode(
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")
        req = request.Request(
            self.token_url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
        token = data.get("access_token")
        if not token:
            raise RuntimeError("Google OAuth token refresh did not return an access token")
        return token

    def _request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        token = self._resolve_access_token()
        url = f"{self.api_base}{path}"
        body = None
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = request.Request(url, data=body, headers=headers, method=method)
        try:
            with request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8") if exc.fp else exc.reason
            raise RuntimeError(f"Google Calendar API request failed: {details}") from exc
