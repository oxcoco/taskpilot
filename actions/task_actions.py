"""Task action wrappers over app/ui and TaskAgent."""

from __future__ import annotations

from typing import Any

from ..agents.task_agent import TaskAgent
from ..agents.deadline_parse import normalize_deadline
from ..app.ui import (
    delete_all_tasks,
    delete_task_by_id,
    edit_task,
    list_all_tasks,
    mark_done,
    mark_undone,
)
from ..database.models import TaskStatus
from ..mcp.todo_server import create_task as mcp_create_task
from .task_resolver import resolve_task_reference


def list_tasks_action(status: str | None = None) -> list[dict[str, Any]]:
    tasks = list_all_tasks()
    if status:
        tasks = [t for t in tasks if t.get("status", "").upper() == status.upper()]
    return tasks


def get_task_action(task_id: str | None = None, reference: str | None = None) -> dict[str, Any]:
    resolved_id = task_id
    if not resolved_id and reference:
        resolved_id = resolve_task_reference(reference)
    if not resolved_id:
        raise ValueError("Task not found")
    task = TaskAgent.get_task(resolved_id)
    if not task:
        raise ValueError(f"Task {resolved_id!r} not found")
    return task.to_dict()


def create_tasks_action(
    text: str | None = None,
    title: str | None = None,
    description: str = "",
    deadline: str | None = None,
    priority: str = "MEDIUM",
    estimated_hours: float = 1.0,
) -> dict[str, Any]:
    created: list[dict[str, Any]] = []
    if text:
        tasks = TaskAgent().extract_tasks(text)
        for task in tasks:
            mcp_create_task(
                title=task.title,
                deadline=task.deadline,
                description=task.description,
                priority=task.priority.name,
                estimated_hours=task.estimated_hours,
            )
            created.append(task.to_dict())
    elif title:
        normalized_deadline = normalize_deadline(deadline) if deadline else None
        task = mcp_create_task(
            title=title,
            description=description,
            deadline=normalized_deadline,
            priority=priority,
            estimated_hours=estimated_hours,
        )
        created.append(task.to_dict())
    else:
        raise ValueError("Provide either 'text' for NLP parsing or 'title' for structured create")
    return {"created": created, "count": len(created)}


def update_task_action(
    task_id: str | None = None,
    reference: str | None = None,
    **updates: Any,
) -> dict[str, Any]:
    resolved_id = task_id or (resolve_task_reference(reference) if reference else None)
    if not resolved_id:
        raise ValueError("Task not found")
    if "deadline" in updates and updates["deadline"]:
        updates = dict(updates)
        updates["deadline"] = normalize_deadline(str(updates["deadline"]))
    edit_task(resolved_id, **updates)
    task = TaskAgent.get_task(resolved_id)
    return {"updated": task.to_dict() if task else {"id": resolved_id}}


def delete_task_action(task_id: str | None = None, reference: str | None = None) -> dict[str, Any]:
    resolved_id = task_id or (resolve_task_reference(reference) if reference else None)
    if not resolved_id:
        raise ValueError("Task not found")
    task = TaskAgent.get_task(resolved_id)
    title = task.title if task else resolved_id
    delete_task_by_id(resolved_id)
    return {"deleted_id": resolved_id, "title": title}


def delete_all_tasks_action() -> dict[str, Any]:
    count = len(list_all_tasks())
    delete_all_tasks()
    return {"deleted_count": count}


def mark_task_done_action(task_id: str | None = None, reference: str | None = None) -> dict[str, Any]:
    resolved_id = task_id or (resolve_task_reference(reference) if reference else None)
    if not resolved_id:
        raise ValueError("Task not found")
    mark_done(resolved_id)
    task = TaskAgent.get_task(resolved_id)
    return {"task": task.to_dict() if task else {"id": resolved_id, "status": TaskStatus.COMPLETED.value}}


def mark_task_undone_action(task_id: str | None = None, reference: str | None = None) -> dict[str, Any]:
    resolved_id = task_id or (resolve_task_reference(reference) if reference else None)
    if not resolved_id:
        raise ValueError("Task not found")
    mark_undone(resolved_id)
    task = TaskAgent.get_task(resolved_id)
    return {"task": task.to_dict() if task else {"id": resolved_id, "status": TaskStatus.PENDING.value}}
