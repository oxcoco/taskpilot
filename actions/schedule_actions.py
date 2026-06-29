"""Schedule and calendar action wrappers."""

from __future__ import annotations

from typing import Any

from ..agents.priority_agent import PriorityAgent
from ..agents.scheduler_agent import SchedulerAgent
from ..agents.task_agent import TaskAgent
from ..mcp.calendar_server import list_events
from ..skills.weekly_plan import generate_weekly_plan


def get_schedule_action(persist: bool = False) -> dict[str, Any]:
    tasks = TaskAgent.list_tasks()
    pending_tasks = [t for t in tasks if t.status.value != "COMPLETED"]
    completed_tasks = [t for t in tasks if t.status.value == "COMPLETED"]

    schedule: dict[str, list[str]] = {}
    if pending_tasks:
        pending_dicts = [t.to_dict() for t in pending_tasks]
        ranked = PriorityAgent().rank_tasks(pending_dicts)
        if persist:
            schedule = SchedulerAgent.generate_schedule(ranked) or {}
        else:
            schedule = _preview_schedule(ranked)

    if completed_tasks:
        schedule["Completed"] = [t.title for t in completed_tasks]

    return {"schedule": schedule}


def _preview_schedule(ranked: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Build schedule without persisting calendar events."""
    # Reuse scheduler logic but skip _persist_schedule by copying core algorithm
    # For preview we call generate_schedule on a copy – it will persist.
    # Instead duplicate lightweight preview: use same method but mock is heavy.
    # Simplest: call generate_schedule only when persist=True; for preview rank only.
    from ..agents.scheduler_agent import SchedulerAgent

    original_persist = SchedulerAgent._persist_schedule

    def noop(_schedule: dict[str, list[str]]) -> None:
        pass

    try:
        SchedulerAgent._persist_schedule = staticmethod(noop)  # type: ignore[method-assign]
        return SchedulerAgent.generate_schedule(ranked) or {}
    finally:
        SchedulerAgent._persist_schedule = original_persist  # type: ignore[method-assign]


def generate_and_persist_schedule_action() -> dict[str, Any]:
    return get_schedule_action(persist=True)


def generate_weekly_plan_action() -> dict[str, Any]:
    plan = generate_weekly_plan()
    return {"plan": plan}


def list_calendar_events_action() -> dict[str, Any]:
    events = list_events()
    serialized = []
    for event in events:
        serialized.append(
            {
                "id": event["id"],
                "title": event["title"],
                "start": event["start"].isoformat(),
                "end": event["end"].isoformat(),
                "description": event.get("description", ""),
            }
        )
    return {"events": serialized}
