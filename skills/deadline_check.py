"""Structured deadline summary for tasks."""

from __future__ import annotations

import datetime
from typing import Any

from ..database.db import list_tasks
from ..database.models import Task, TaskStatus


def _parse_deadline_date(deadline: str, today: datetime.date) -> datetime.date | None:
    try:
        return datetime.datetime.strptime(deadline, "%Y-%m-%d").date()
    except ValueError:
        word = deadline.lower()
        if word == "today":
            return today
        if word == "tomorrow":
            return today + datetime.timedelta(days=1)
        return None


def _task_to_summary(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "deadline": task.deadline,
        "priority": task.priority.value,
        "status": task.status.value,
    }


def get_deadline_summary(upcoming_days: int = 3) -> dict[str, list[dict[str, Any]]]:
    """Return overdue, upcoming, and completed tasks with deadlines."""
    today = datetime.date.today()
    horizon = today + datetime.timedelta(days=upcoming_days)
    overdue: list[dict[str, Any]] = []
    upcoming: list[dict[str, Any]] = []
    completed: list[dict[str, Any]] = []

    for task in list_tasks():
        if not task.deadline:
            continue
        deadline_date = _parse_deadline_date(task.deadline, today)
        if deadline_date is None:
            continue

        summary = _task_to_summary(task)
        if task.status == TaskStatus.COMPLETED:
            completed.append(summary)
        elif deadline_date < today:
            overdue.append(summary)
        elif today <= deadline_date <= horizon:
            upcoming.append(summary)

    return {"overdue": overdue, "upcoming": upcoming, "completed": completed}


def check_deadlines() -> None:
    """CLI wrapper: print deadline summary."""
    data = get_deadline_summary(upcoming_days=7)
    overdue = data["overdue"]
    upcoming = data["upcoming"]
    completed = data["completed"]

    if overdue:
        print("[DeadlineCheck] Overdue tasks:")
        for t in overdue:
            print(f"  - {t['title']} (ID: {t['id']}) deadline: {t['deadline']}")
    else:
        print("[DeadlineCheck] No overdue tasks.")

    if upcoming:
        print("[DeadlineCheck] Upcoming tasks (next 7 days):")
        for t in upcoming:
            print(f"  - {t['title']} (ID: {t['id']}) deadline: {t['deadline']}")

    if completed:
        print("[DeadlineCheck] Completed tasks with deadlines:")
        for t in completed:
            print(f"  - {t['title']} (ID: {t['id']}) deadline: {t['deadline']}")
