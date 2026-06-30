"""Tests for the direct Google Calendar export API endpoint."""

import pytest

from taskpilot.app.api import app as flask_app


def test_direct_google_calendar_export_endpoint(monkeypatch):
    captured = {}

    def fake_export_tasks_to_google_calendar_action(**kwargs):
        captured.update(kwargs)
        return {
            "calendar_id": "primary",
            "timezone": "UTC",
            "exported_count": 3,
            "skipped_count": 0,
            "created_events": [],
            "skipped_tasks": [],
        }

    monkeypatch.setattr(
        "taskpilot.app.api.export_tasks_to_google_calendar_action",
        fake_export_tasks_to_google_calendar_action,
    )

    client = flask_app.test_client()
    response = client.post(
        "/api/google_calendar/export",
        json={"include_completed": True, "include_undated": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["exported_count"] == 3
    assert captured["include_completed"] is True
    assert captured["include_undated"] is True
