# taskpilot/database/db.py
"""SQLite database layer for TaskPilot.

Provides simple CRUD operations for :class:`~taskpilot.database.models.Task`.
All functions use the built‑in ``sqlite3`` module and return Python objects
or ``None`` where appropriate.
"""

from __future__ import annotations

import os
import sqlite3
from typing import List, Optional

from .models import Task, TaskStatus

# Determine the path to the SQLite database file. It lives one directory up
# from this module (``taskpilot/database/sqlite.db``). Using an absolute path
# makes the functions safe to call from any working directory.
_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sqlite.db"))


def _connect() -> sqlite3.Connection:
    """Create a new SQLite connection.

    The connection uses row factory ``sqlite3.Row`` so column names can be
    accessed like a mapping, which simplifies conversion to :class:`Task`.
    """
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables() -> None:
    """Create the ``tasks`` table if it does not already exist.

    The schema mirrors the fields of :class:`Task`. ``id`` is the primary key
    because it is a unique string (e.g., a UUID).
    """
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                deadline TEXT,
                priority TEXT NOT NULL,
                estimated_hours REAL NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        conn.commit()


def add_task(task: Task) -> None:
    """Insert a new task into the database.

    Parameters
    ----------
    task: Task
        The task instance to store. ``task.id`` must be unique.
    """
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO tasks (id, title, description, deadline, priority, estimated_hours, status)
            VALUES (:id, :title, :description, :deadline, :priority, :estimated_hours, :status)
            """,
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "deadline": task.deadline,
                "priority": task.priority.value,
                "estimated_hours": task.estimated_hours,
                "status": task.status.value,
            },
        )
        conn.commit()


def update_task(task: Task) -> None:
    """Update an existing task.

    The task is identified by its ``id``. All fields are overwritten with the
    values from the supplied ``Task`` instance.
    """
    with _connect() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET title = :title,
                description = :description,
                deadline = :deadline,
                priority = :priority,
                estimated_hours = :estimated_hours,
                status = :status
            WHERE id = :id
            """,
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "deadline": task.deadline,
                "priority": task.priority.value,
                "estimated_hours": task.estimated_hours,
                "status": task.status.value,
            },
        )
        conn.commit()


def delete_task(task_id: str) -> None:
    """Remove a task from the database by its ``id``.
    """
    with _connect() as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()


def get_task(task_id: str) -> Optional[Task]:
    """Fetch a single task by ``id``.

    Returns ``None`` if the task does not exist.
    """
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        return Task.from_dict(dict(row))


def list_tasks() -> List[Task]:
    """Return a list of all stored tasks ordered by ``deadline``.
    """
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY deadline").fetchall()
        return [Task.from_dict(dict(r)) for r in rows]
