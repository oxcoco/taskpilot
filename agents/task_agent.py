# taskpilot/agents/task_agent.py
"""TaskAgent – extracts structured tasks from natural language.

Now returns :class:`taskpilot.database.models.Task` instances instead of raw
dictionaries, matching the expectations of the CoordinatorAgent.
"""

from __future__ import annotations

import re
import uuid
import datetime
from typing import List

from ..database.models import Task, TaskPriority, TaskStatus
from ..mcp.todo_server import (
    create_task as mcp_create_task,
    update_task as mcp_update_task,
    delete_task as mcp_delete_task,
    get_task as mcp_get_task,
    list_tasks as mcp_list_tasks,
)


def _normalize_deadline(deadline: str | None) -> str | None:
    """Convert a deadline string (e.g., "today", "tomorrow", weekday, ISO) to an ISO date.

    Returns the ISO string (YYYY‑MM‑DD) if parsing succeeds, otherwise returns the original value.
    """
    if not deadline:
        return None
    today = datetime.date.today()
    w = deadline.lower().strip()
    # ISO format
    try:
        return datetime.datetime.strptime(w, "%Y-%m-%d").date().isoformat()
    except Exception:
        pass
    if w == "today":
        return today.isoformat()
    if w == "tomorrow":
        return (today + datetime.timedelta(days=1)).isoformat()
    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    if w in weekdays:
        target = weekdays[w]
        days_ahead = (target - today.weekday()) % 7
        return (today + datetime.timedelta(days=days_ahead)).isoformat()
    if w.startswith("next "):
        day_name = w.split(" ", 1)[1]
        if day_name in weekdays:
            target = weekdays[day_name]
            days_ahead = (target - today.weekday()) % 7
            days_ahead = days_ahead or 7
            return (today + datetime.timedelta(days=days_ahead)).isoformat()
    # fallback
    return deadline


class TaskAgent:
    """Parse free‑form text into :class:`Task` objects.

    Simple heuristic:
    * Split on punctuation or the word ``and``.
    * Detect a trailing ``by <deadline>`` phrase.
    * Generate a UUID for each task.
    * Populate default values for other fields; priority will be set later.
    """

    @staticmethod
    def _parse_fragment(fragment: str) -> Task:
        fragment = fragment.strip()
        # Detect "by <deadline>" at the end.
        match = re.search(
            r"(?P<title>.+?)\s+by\s+(?P<deadline>\w+)$", fragment, flags=re.IGNORECASE
        )
        if match:
            title = match.group("title").strip()
            raw_deadline = match.group("deadline").strip()
            deadline = _normalize_deadline(raw_deadline)
        else:
            title = fragment
            deadline = None
        return Task(
            id=str(uuid.uuid4()),
            title=title,
            description="",
            deadline=deadline,
            priority=TaskPriority.MEDIUM,
            estimated_hours=1.0,
            status=TaskStatus.PENDING,
        )

    def extract_tasks(self, text: str) -> List[Task]:
        """Extract a list of :class:`Task` objects from *text*.

        The text may contain multiple sentences separated by punctuation or the
        conjunction ``and``. Each fragment is parsed independently.
        """
        fragments = re.split(r"[.;\n]+|\band\b", text, flags=re.IGNORECASE)
        tasks: List[Task] = []
        for frag in fragments:
            if frag.strip():
                tasks.append(self._parse_fragment(frag))
        return tasks

    @staticmethod
    def list_tasks() -> List[Task]:
        """Return all tasks via MCP."""
        return mcp_list_tasks()

    @staticmethod
    def get_task(task_id: str) -> Task | None:
        """Retrieve a single task via MCP. Returns ``None`` if not found."""
        return mcp_get_task(task_id)

    @staticmethod
    def update_task(task: Task) -> None:
        """Update a task via MCP (status, fields)."""
        mcp_update_task(task)

    @staticmethod
    def delete_task(task_id: str) -> None:
        """Delete a task via MCP."""
        mcp_delete_task(task_id)

    @staticmethod
    def set_status(task_id: str, status: TaskStatus) -> None:
        """Set the status of a task (COMPLETED/PENDING)."""
        task = TaskAgent.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        task.status = status
        TaskAgent.update_task(task)

    @staticmethod
    def create_tasks(tasks: List[Task]) -> None:
        """Create multiple tasks via the DB, preserving task IDs.

        This avoids the UUID regeneration performed by the MCP create_task façade.
        """
        from ..database.db import add_task as db_add_task

        for t in tasks:
            db_add_task(t)
