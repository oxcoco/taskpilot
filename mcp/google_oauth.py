"""Google OAuth helpers for TaskPilot backend routes."""

from __future__ import annotations

import json
from typing import Any
from urllib import parse, request

GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def build_google_authorization_url(
    client_id: str,
    redirect_uri: str,
    state: str,
    scopes: list[str] | None = None,
) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes or GOOGLE_CALENDAR_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{GOOGLE_AUTHORIZATION_URL}?{parse.urlencode(params)}"


def exchange_code_for_tokens(
    *,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict[str, Any]:
    payload = parse.urlencode(
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    req = request.Request(
        GOOGLE_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))
