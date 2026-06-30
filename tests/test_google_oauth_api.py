"""Tests for the Google OAuth connect flow."""

from taskpilot.app.api import app as flask_app
from taskpilot.database.google_oauth import GoogleOAuthCredentials


def test_google_calendar_connect_redirects_to_google(monkeypatch):
    captured = {}

    def fake_build_google_authorization_url(**kwargs):
        captured.update(kwargs)
        return "https://accounts.google.com/mock-auth"

    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setattr(
        "taskpilot.app.api.build_google_authorization_url",
        fake_build_google_authorization_url,
    )

    client = flask_app.test_client()
    response = client.get("/api/google-calendar/connect?return_to=http://localhost:5173")

    assert response.status_code == 302
    assert response.location == "https://accounts.google.com/mock-auth"
    assert captured["client_id"] == "client-id"
    assert captured["state"]

    with client.session_transaction() as session:
        assert session["google_oauth_state"] == captured["state"]
        assert session["google_oauth_return_to"] == "http://localhost:5173"


def test_google_calendar_callback_saves_refresh_token(monkeypatch):
    saved = {}

    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(
        "taskpilot.app.api.exchange_code_for_tokens",
        lambda **kwargs: {
            "refresh_token": "refresh-token-123",
            "scope": "https://www.googleapis.com/auth/calendar.events",
        },
    )
    monkeypatch.setattr(
        "taskpilot.app.api.save_google_oauth_credentials",
        lambda **kwargs: saved.update(kwargs),
    )

    client = flask_app.test_client()
    with client.session_transaction() as session:
        session["google_oauth_state"] = "expected-state"
        session["google_oauth_return_to"] = "http://localhost:5173"

    response = client.get("/api/google-calendar/callback?code=auth-code&state=expected-state")

    assert response.status_code == 302
    assert response.location == "http://localhost:5173?google_calendar=connected"
    assert saved["refresh_token"] == "refresh-token-123"
    assert saved["scope"] == "https://www.googleapis.com/auth/calendar.events"


def test_google_calendar_status_reports_connection(monkeypatch):
    monkeypatch.setattr(
        "taskpilot.app.api.load_google_oauth_credentials",
        lambda: GoogleOAuthCredentials(refresh_token="refresh-token-123"),
    )

    client = flask_app.test_client()
    response = client.get("/api/google-calendar/status")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["connected"] is True
