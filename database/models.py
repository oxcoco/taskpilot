# taskpilot/database/models.py
"""Database models for TaskPilot.

Defines the `Task` dataclass representing a single task entity.
It includes type hints, default values, and enumerations for
status and priority to ensure consistency across the codebase.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TaskStatus(str, Enum):
    """Allowed status values for a task."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class TaskPriority(str, Enum):
    """Allowed priority levels for a task."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Task:
    """Dataclass representing a task.

    Attributes
    ----------
    id: str
        Unique identifier for the task (UUID string).
    title: str
        Short title of the task.
    description: str
        Detailed description; may be empty.
    deadline: Optional[str]
        Optional deadline expressed as an ISO‑8601 date string or free‑form text.
    priority: TaskPriority
        Priority level; defaults to ``MEDIUM``.
    estimated_hours: float
        Approximate effort in hours; defaults to ``1.0``.
    status: TaskStatus
        Current state of the task; defaults to ``PENDING``.
    """

    id: str
    title: str
    description: str = ""
    deadline: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    estimated_hours: float = 1.0
    status: TaskStatus = TaskStatus.PENDING

    def to_dict(self) -> dict:
        """Return a plain dictionary representation of the task.

        Mirrors the structure used by UI helpers for easy JSON‑compatible output.
        """
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "deadline": self.deadline,
            "priority": self.priority.value,
            "estimated_hours": self.estimated_hours,
            "status": self.status.value,
        }

    @staticmethod
    def from_dict(data: dict) -> "Task":
        """Create a ``Task`` instance from a dictionary.

        Parameters
        ----------
        data: dict
            Mapping with keys matching :meth:`to_dict` output.
        """
        return Task(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            deadline=data.get("deadline"),
            priority=TaskPriority(data.get("priority", TaskPriority.MEDIUM.value)),
            estimated_hours=float(data.get("estimated_hours", 1.0)),
            status=TaskStatus(data.get("status", TaskStatus.PENDING.value)),
        )
