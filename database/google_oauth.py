"""SQLite storage for TaskPilot Google OAuth credentials."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .db import _connect

_GOOGLE_OAUTH_ROW_ID = "default"


@dataclass
class GoogleOAuthCredentials:
    refresh_token: str
    scope: str | None = None
    email: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


def ensure_google_oauth_table() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS google_oauth_credentials (
                id TEXT PRIMARY KEY,
                refresh_token TEXT NOT NULL,
                scope TEXT,
                email TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_google_oauth_credentials(
    refresh_token: str,
    scope: str | None = None,
    email: str | None = None,
) -> None:
    ensure_google_oauth_table()
    now = datetime.utcnow().isoformat()
    with _connect() as conn:
        existing = conn.execute(
            "SELECT created_at FROM google_oauth_credentials WHERE id = ?",
            (_GOOGLE_OAUTH_ROW_ID,),
        ).fetchone()
        created_at = existing["created_at"] if existing else now
        conn.execute(
            """
            INSERT INTO google_oauth_credentials
                (id, refresh_token, scope, email, created_at, updated_at)
            VALUES
                (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                refresh_token = excluded.refresh_token,
                scope = excluded.scope,
                email = excluded.email,
                updated_at = excluded.updated_at
            """,
            (_GOOGLE_OAUTH_ROW_ID, refresh_token, scope, email, created_at, now),
        )
        conn.commit()


def load_google_oauth_credentials() -> GoogleOAuthCredentials | None:
    ensure_google_oauth_table()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM google_oauth_credentials WHERE id = ?",
            (_GOOGLE_OAUTH_ROW_ID,),
        ).fetchone()
        if row is None:
            return None
        return GoogleOAuthCredentials(
            refresh_token=row["refresh_token"],
            scope=row["scope"],
            email=row["email"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def delete_google_oauth_credentials() -> None:
    ensure_google_oauth_table()
    with _connect() as conn:
        conn.execute(
            "DELETE FROM google_oauth_credentials WHERE id = ?",
            (_GOOGLE_OAUTH_ROW_ID,),
        )
        conn.commit()


def google_oauth_connected() -> bool:
    return load_google_oauth_credentials() is not None
