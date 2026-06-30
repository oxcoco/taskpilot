"""Canonical action registry for TaskPilot chatbot and tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

from ..skills.deadline_check import get_deadline_summary
from .schedule_actions import (
    generate_and_persist_schedule_action,
    export_tasks_to_google_calendar_action,
    generate_weekly_plan_action,
    get_schedule_action,
    list_calendar_events_action,
)
from .task_actions import (
    create_tasks_action,
    delete_all_tasks_action,
    delete_task_action,
    get_task_action,
    list_tasks_action,
    mark_task_done_action,
    mark_task_undone_action,
    update_task_action,
)


@dataclass
class ActionSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    requires_approval: bool
    handler: Callable[..., Any]
    category: Literal["read", "mutate"]
    destructive: bool = False
    artifact_type: str | None = None


class ActionRegistry:
    """Registry of all chatbot-accessible actions."""

    def __init__(self) -> None:
        self._specs: dict[str, ActionSpec] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(
            ActionSpec(
                name="list_tasks",
                description=(
                    "List the user's tasks. Use when they ask to see, show, or list tasks. "
                    "Returns title, deadline, priority, status, and estimated hours for each task."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["PENDING", "IN_PROGRESS", "COMPLETED"],
                            "description": "Optional status filter",
                        }
                    },
                },
                requires_approval=False,
                handler=lambda **kw: {"tasks": list_tasks_action(kw.get("status"))},
                category="read",
                artifact_type="task_list",
            )
        )
        self.register(
            ActionSpec(
                name="get_task",
                description=(
                    "Look up one task by list number (1, 2, 3…), UUID, or a unique title fragment. "
                    "Use when the user asks about a specific task."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "reference": {"type": "string", "description": "Title fragment or list index"},
                    },
                },
                requires_approval=False,
                handler=lambda **kw: {"task": get_task_action(kw.get("task_id"), kw.get("reference"))},
                category="read",
            )
        )
        self.register(
            ActionSpec(
                name="check_deadlines",
                description=(
                    "Report overdue tasks and tasks due in the next 3 days. "
                    "Use when the user asks about deadlines, due dates, what's overdue, or what's coming up."
                ),
                parameters={"type": "object", "properties": {}},
                requires_approval=False,
                handler=lambda **_kw: get_deadline_summary(),
                category="read",
                artifact_type="deadline_summary",
            )
        )
        self.register(
            ActionSpec(
                name="generate_weekly_plan",
                description=(
                    "Generate a narrative weekly work plan using AI. "
                    "Use when the user wants help planning their week, prioritizing work, or deciding what to focus on each day."
                ),
                parameters={"type": "object", "properties": {}},
                requires_approval=False,
                handler=lambda **_kw: generate_weekly_plan_action(),
                category="read",
                artifact_type="weekly_plan",
            )
        )
        self.register(
            ActionSpec(
                name="get_schedule",
                description=(
                    "Preview a day-by-day work schedule for pending tasks (read-only, does not save). "
                    "Use when the user asks what to work on when, or wants a schedule/timeline view."
                ),
                parameters={"type": "object", "properties": {}},
                requires_approval=False,
                handler=lambda **_kw: get_schedule_action(persist=False),
                category="read",
                artifact_type="schedule",
            )
        )
        self.register(
            ActionSpec(
                name="list_calendar_events",
                description=(
                    "List calendar events previously saved by schedule generation. "
                    "Use when the user asks about calendar events or saved schedule blocks."
                ),
                parameters={"type": "object", "properties": {}},
                requires_approval=False,
                handler=lambda **_kw: list_calendar_events_action(),
                category="read",
            )
        )
        self.register(
            ActionSpec(
                name="create_tasks",
                description=(
                    "Create one or more tasks. "
                    "PREFERRED: pass structured fields `title` and `deadline` separately. "
                    "Deadline accepts: today, tomorrow, weekday names (friday), next weekday (next monday), "
                    "ISO dates (2026-07-03), or US dates (7/3/2026). "
                    "ALTERNATIVE: pass a single `text` string like 'Finish report by Friday'. "
                    "Do not include the deadline inside `title` when using structured fields."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Task title only, without deadline phrasing.",
                        },
                        "deadline": {
                            "type": "string",
                            "description": (
                                "Due date: today | tomorrow | monday | next friday | 2026-07-03 | 7/3/2026"
                            ),
                        },
                        "text": {
                            "type": "string",
                            "description": (
                                "Full natural-language task phrase when not using title/deadline fields, "
                                "e.g. 'Finish chemistry lab by next Friday'."
                            ),
                        },
                        "description": {"type": "string", "description": "Optional longer notes."},
                        "priority": {
                            "type": "string",
                            "enum": ["HIGH", "MEDIUM", "LOW"],
                            "description": "Default MEDIUM if omitted.",
                        },
                        "estimated_hours": {
                            "type": "number",
                            "description": "Estimated effort in hours. Default 1.0.",
                        },
                    },
                },
                requires_approval=True,
                handler=create_tasks_action,
                category="mutate",
            )
        )
        self.register(
            ActionSpec(
                name="update_task",
                description=(
                    "Update an existing task's fields. "
                    "Identify the task with `reference` (title fragment or list number) or `task_id`. "
                    "Deadline format matches create_tasks."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task UUID if known."},
                        "reference": {
                            "type": "string",
                            "description": "Title fragment or list index, e.g. 'chemistry' or '2'.",
                        },
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "deadline": {
                            "type": "string",
                            "description": "today | tomorrow | friday | next monday | 2026-07-03",
                        },
                        "priority": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
                        "estimated_hours": {"type": "number"},
                        "status": {"type": "string", "enum": ["PENDING", "IN_PROGRESS", "COMPLETED"]},
                    },
                },
                requires_approval=True,
                handler=update_task_action,
                category="mutate",
            )
        )
        self.register(
            ActionSpec(
                name="delete_task",
                description=(
                    "Delete a single task. "
                    "Use `reference` (title fragment or list number) or `task_id`."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "reference": {"type": "string"},
                    },
                },
                requires_approval=True,
                handler=delete_task_action,
                category="mutate",
            )
        )
        self.register(
            ActionSpec(
                name="delete_all_tasks",
                description=(
                    "Delete every task. Destructive. "
                    "Use only when the user explicitly asks to clear or delete all tasks."
                ),
                parameters={"type": "object", "properties": {}},
                requires_approval=True,
                handler=lambda **_kw: delete_all_tasks_action(),
                category="mutate",
                destructive=True,
            )
        )
        self.register(
            ActionSpec(
                name="mark_task_done",
                description=(
                    "Mark a task completed. "
                    "Use `reference` (title fragment or list number) or `task_id`."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "reference": {"type": "string"},
                    },
                },
                requires_approval=True,
                handler=mark_task_done_action,
                category="mutate",
            )
        )
        self.register(
            ActionSpec(
                name="mark_task_undone",
                description=(
                    "Mark a completed task as pending again. "
                    "Use `reference` or `task_id`."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "reference": {"type": "string"},
                    },
                },
                requires_approval=True,
                handler=mark_task_undone_action,
                category="mutate",
            )
        )
        self.register(
            ActionSpec(
                name="generate_and_persist_schedule",
                description=(
                    "Build a day-by-day schedule and save calendar events. "
                    "Use when the user wants to generate and save a schedule, not just preview it."
                ),
                parameters={"type": "object", "properties": {}},
                requires_approval=True,
                handler=lambda **_kw: generate_and_persist_schedule_action(),
                category="mutate",
                artifact_type="schedule",
            )
        )
        self.register(
            ActionSpec(
                name="export_tasks_to_google_calendar",
                description=(
                    "Export one or more tasks to the user's Google Calendar. "
                    "Use when the user asks to send, sync, or export tasks to Google Calendar."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "task_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional task IDs to export. Defaults to all non-completed tasks.",
                        },
                        "calendar_id": {
                            "type": "string",
                            "description": "Optional Google Calendar ID. Defaults to primary.",
                        },
                        "timezone": {
                            "type": "string",
                            "description": "Optional event timezone, e.g. America/New_York.",
                        },
                        "include_completed": {
                            "type": "boolean",
                            "description": "Include completed tasks in the export.",
                        },
                        "include_undated": {
                            "type": "boolean",
                            "description": "Place undated tasks on today instead of skipping them.",
                        },
                    },
                },
                requires_approval=True,
                handler=export_tasks_to_google_calendar_action,
                category="mutate",
            )
        )

    def register(self, spec: ActionSpec) -> None:
        self._specs[spec.name] = spec

    def get(self, name: str) -> ActionSpec:
        if name not in self._specs:
            raise KeyError(f"Unknown action: {name!r}")
        return self._specs[name]

    def all_specs(self) -> list[ActionSpec]:
        return list(self._specs.values())

    def execute(self, name: str, payload: dict[str, Any]) -> Any:
        spec = self.get(name)
        if spec.requires_approval:
            raise PermissionError(
                f"Action {name!r} requires approval and cannot be executed directly"
            )
        return spec.handler(**payload)

    def execute_approved(self, name: str, payload: dict[str, Any]) -> Any:
        """Execute a mutating action after user approval."""
        spec = self.get(name)
        return spec.handler(**payload)

    def summarize(self, name: str, payload: dict[str, Any]) -> str:
        if name == "create_tasks":
            if payload.get("title"):
                title = payload.get("title", "Untitled")
                deadline = payload.get("deadline")
                extra = f" due {deadline}" if deadline else ""
                return f"Create task: {title}{extra}"
            if payload.get("text"):
                return f"Create task(s) from: \"{payload['text']}\""
        if name == "delete_task":
            ref = payload.get("reference") or payload.get("task_id", "unknown")
            return f"Delete task: {ref}"
        if name == "delete_all_tasks":
            return "Delete ALL tasks (destructive)"
        if name == "update_task":
            ref = payload.get("reference") or payload.get("task_id", "task")
            fields = [k for k in payload if k not in ("task_id", "reference")]
            return f"Update {ref}: {', '.join(fields)}"
        if name == "mark_task_done":
            ref = payload.get("reference") or payload.get("task_id", "task")
            return f"Mark complete: {ref}"
        if name == "mark_task_undone":
            ref = payload.get("reference") or payload.get("task_id", "task")
            return f"Mark pending: {ref}"
        if name == "generate_and_persist_schedule":
            return "Generate schedule and save calendar events"
        if name == "export_tasks_to_google_calendar":
            count = len(payload.get("task_ids", [])) if payload.get("task_ids") else "all eligible"
            return f"Export {count} task(s) to Google Calendar"
        return f"Execute {name}"

    def openai_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters,
                },
            }
            for spec in self._specs.values()
        ]


_registry: ActionRegistry | None = None


def get_registry() -> ActionRegistry:
    global _registry
    if _registry is None:
        _registry = ActionRegistry()
    return _registry
