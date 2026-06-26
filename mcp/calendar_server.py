# pyrefly: ignore [missing-import]
"""MCP Calendar Server.

Provides simple CRUD operations for calendar events. The data is stored in a
separate ``events`` table within the same SQLite database used by the task
layer. These functions are intended to be called by the SchedulerAgent before
persisting scheduling results.
"""

import sqlite3
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any

# Use the same database file as the core DB layer.
_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "database", "sqlite.db")
)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_events_table() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                start TEXT NOT NULL,
                end TEXT NOT NULL,
                description TEXT
            )
            """
        )
        conn.commit()


# Ensure the table exists at import time.
_ensure_events_table()


def create_event(
    title: str, start: datetime, end: datetime, description: str = ""
) -> Dict[str, Any]:
    """Create a new calendar event.

    Returns a dictionary representation of the created event.
    """
    if end < start:
        raise ValueError("Event end time must be after start time")
    event_id = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            "INSERT INTO events (id, title, start, end, description) VALUES (?, ?, ?, ?, ?)",
            (event_id, title, start.isoformat(), end.isoformat(), description),
        )
        conn.commit()
    return {
        "id": event_id,
        "title": title,
        "start": start,
        "end": end,
        "description": description,
    }


def update_event(event_id: str, **updates: Any) -> None:
    """Update fields of an existing event.

    Accepted keys: ``title``, ``start``, ``end``, ``description``.
    ``start`` and ``end`` should be ``datetime`` objects.
    """
    allowed = {"title", "start", "end", "description"}
    if not updates:
        return
    for key in updates:
        if key not in allowed:
            raise ValueError(f"Unsupported field {key} for event update")
    set_clause = []
    params = []
    for key, value in updates.items():
        if key in {"start", "end"}:
            value = value.isoformat()
        set_clause.append(f"{key} = ?")
        params.append(value)
    params.append(event_id)
    with _connect() as conn:
        conn.execute(f"UPDATE events SET {', '.join(set_clause)} WHERE id = ?", params)
        conn.commit()


def list_events() -> List[Dict[str, Any]]:
    """Return a list of all calendar events as dictionaries."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM events ORDER BY start").fetchall()
        events = []
        for row in rows:
            events.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "start": datetime.fromisoformat(row["start"]),
                    "end": datetime.fromisoformat(row["end"]),
                    "description": row["description"],
                }
            )
        return events
