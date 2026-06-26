# pyrefly: ignore [missing-import]
"""MCP Todo Server.

Provides a thin façade over the core database layer for task‑management operations.
These functions are intended to be called by higher‑level agents (TaskAgent,
PriorityAgent, SchedulerAgent) before persisting data to the SQLite database.
"""

from ..database.db import (
    add_task as db_add_task,
    update_task as db_update_task,
    delete_task as db_delete_task,
    list_tasks as db_list_tasks,
    get_task as db_get_task,
)
from ..database.models import Task, TaskStatus, TaskPriority
import uuid
from typing import List


def create_task(
    title: str,
    deadline: str | None = None,
    description: str = "",
    priority: str = "MEDIUM",
    estimated_hours: float = 1.0,
) -> Task:
    """Create a new task and store it in the database.

    Returns the created :class:`Task` instance.
    """
    task = Task(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        deadline=deadline,
        priority=TaskPriority[priority.upper()],
        estimated_hours=estimated_hours,
        status=TaskStatus.PENDING,
    )
    db_add_task(task)
    return task


def update_task(task: Task) -> None:
    """Update a task in the database.

    The function expects a full :class:`Task` instance with the desired fields
    (including any modified status) and persists it via the DB layer.
    """
    db_update_task(task)


def delete_task(task_id: str) -> None:
    """Delete a task from the database by its identifier."""
    db_delete_task(task_id)


def list_tasks() -> List[Task]:
    """Return a list of all tasks (as :class:`Task` objects)."""
    return db_list_tasks()


def get_task(task_id: str) -> Task:
    """Retrieve a single task by its identifier."""
    return db_get_task(task_id)
