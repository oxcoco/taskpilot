#!/usr/bin/env python3
"""UI helpers for TaskPilot.

Provides simple functions that can be used by the CLI or other callers to
interact with the task database: list tasks, add a task, edit fields, delete a
task, and toggle its completion status.
"""

from typing import List, Dict, Any
import uuid

from ..database.db import (
    add_task,
    update_task,
    delete_task,
    get_task,
    list_tasks,
    create_tables,
)
# Ensure the SQLite tables exist before any operation.
create_tables()
from ..agents.scheduler_agent import SchedulerAgent
from ..skills.weekly_plan import generate_weekly_plan
from ..skills.deadline_check import check_deadlines
from ..database.models import Task, TaskStatus, TaskPriority


def delete_all_tasks() -> None:
    """Delete every task in the database."""
    for task in list_tasks():
        delete_task(task.id)


def show_schedule() -> None:
    """Generate and display the schedule from SchedulerAgent."""
    # Convert Task objects to dicts for the scheduler
    tasks = [t.to_dict() for t in list_tasks()]
    schedule = SchedulerAgent.generate_schedule(tasks)
    if not schedule:
        print("[TaskPilot] No schedule generated (no tasks).")
        return
    print("[TaskPilot] Generated schedule:")
    for day, titles in schedule.items():
        print(f"  {day}:")
        for title in titles:
            print(f"    - {title}")


def list_all_tasks() -> List[Dict[str, Any]]:
    """Return all tasks as plain dictionaries for easy display."""
    return [t.to_dict() for t in list_tasks()]


def add_task_interactive(title: str, description: str = "", deadline: str = None,
                         priority: str = "MEDIUM", estimated_hours: float = 1.0) -> None:
    """Create and store a new task.

    Parameters are simple strings/values; ``priority`` must be one of the
    ``TaskPriority`` enum names.
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
    add_task(task)


def edit_task(task_id: str, **updates: Any) -> None:
    """Update fields of an existing task.

    ``updates`` may contain any of the Task attributes (title, description,
    deadline, priority, estimated_hours, status). Enum fields accept either the
    enum instance or the string name.
    """
    task = get_task(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")
    for key, value in updates.items():
        if key == "priority" and isinstance(value, str):
            value = TaskPriority[value.upper()]
        if key == "status" and isinstance(value, str):
            value = TaskStatus[value.upper()]
        setattr(task, key, value)
    update_task(task)


def delete_task_by_id(task_id: str) -> None:
    """Remove a task from the database."""
    delete_task(task_id)


def mark_done(task_id: str) -> None:
    """Mark a task as completed."""
    edit_task(task_id, status=TaskStatus.COMPLETED)


def mark_undone(task_id: str) -> None:
    """Mark a task as not completed (pending)."""
    edit_task(task_id, status=TaskStatus.PENDING)
