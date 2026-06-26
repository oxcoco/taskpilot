#!/usr/bin/env python3
"""UI helpers for TaskPilot.

Provides simple functions that can be used by the CLI or other callers to
interact with the task database: list tasks, add a task, edit fields, delete a
task, and toggle its completion status.
"""

from typing import List, Dict, Any
import uuid

from ..agents.task_agent import TaskAgent
from ..database.db import create_tables
from ..database.models import TaskStatus, TaskPriority
# Ensure the SQLite tables exist before any operation.
create_tables()  # keep table creation but DB functions are no longer imported directly
from ..agents.scheduler_agent import SchedulerAgent

from ..mcp.todo_server import create_task as mcp_create_task
from ..skills.deadline_check import check_deadlines
from ..skills.weekly_plan import generate_weekly_plan
from ..agents.priority_agent import PriorityAgent

def delete_all_tasks() -> None:
    """Delete every task in the database."""
    for task in TaskAgent.list_tasks():
        TaskAgent.delete_task(task.id)


def show_schedule() -> None:
    """Generate and display the schedule, respecting priority and persisting to calendar."""
    # Load all tasks from DB
    tasks = TaskAgent.list_tasks()
    # Convert to simple dicts for downstream agents
    task_dicts: List[Dict[str, Any]] = [t.to_dict() for t in tasks]
    # Rank tasks by priority
    ranked = PriorityAgent().rank_tasks(task_dicts)
    # Generate schedule (this will also persist events via MCP)
    schedule = SchedulerAgent.generate_schedule(ranked)
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
    return [t.to_dict() for t in TaskAgent.list_tasks()]


def add_task_interactive(title: str, description: str = "", deadline: str = None,
                          priority: str = "MEDIUM", estimated_hours: float = 1.0) -> None:
    """Create and store a new task via the MCP todo server using TaskAgent parsing.
    The provided fields are concatenated into a simple natural‑language description
    which TaskAgent parses into one or more :class:`Task` objects. Each resulting
    task is persisted via the MCP façade.
    """
    # Combine fields into a single description for the TaskAgent
    raw_input = f"{title}"
    if description:
        raw_input += f" {description}"
    if deadline:
        raw_input += f" by {deadline}"
    # Extract task objects
    tasks = TaskAgent().extract_tasks(raw_input)
    for task in tasks:
        # Use the MCP create_task to persist
        mcp_create_task(
            title=task.title,
            deadline=task.deadline,
            description=task.description,
            priority=task.priority.name,
            estimated_hours=task.estimated_hours,
        )


def edit_task(task_id: str, **updates: Any) -> None:
    """Update fields of an existing task.

    ``updates`` may contain any of the Task attributes (title, description,
    deadline, priority, estimated_hours, status). Enum fields accept either the
    enum instance or the string name.
    """
    task = TaskAgent.get_task(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")
    for key, value in updates.items():
        if key == "priority" and isinstance(value, str):
            value = TaskPriority[value.upper()]
        if key == "status" and isinstance(value, str):
            value = TaskStatus[value.upper()]
        setattr(task, key, value)
    TaskAgent.update_task(task)


def delete_task_by_id(task_id: str) -> None:
    """Remove a task from the database."""
    TaskAgent.delete_task(task_id)


def mark_done(task_id: str) -> None:
    """Mark a task as completed."""
    TaskAgent.set_status(task_id, TaskStatus.COMPLETED)


def mark_undone(task_id: str) -> None:
    """Mark a task as not completed (pending)."""
    TaskAgent.set_status(task_id, TaskStatus.PENDING)
