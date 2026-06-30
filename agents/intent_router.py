"""Rule-based intent routing fallback when LLM is unavailable."""

from __future__ import annotations

import re
from typing import Any


def route_message(message: str) -> dict[str, Any] | None:
    """Return {action_name, payload} for simple keyword matches, or None."""
    text = message.strip().lower()
    if not text:
        return None

    if any(kw in text for kw in ("deadline", "overdue", "due soon", "coming up")):
        return {"action_name": "check_deadlines", "payload": {}}

    if any(kw in text for kw in ("weekly plan", "plan my week", "week plan")):
        return {"action_name": "generate_weekly_plan", "payload": {}}

    if re.search(r"\b(schedule|what should i work on|timeline)\b", text):
        if "save" in text or "persist" in text or "calendar" in text:
            return {"action_name": "generate_and_persist_schedule", "payload": {}}
        return {"action_name": "get_schedule", "payload": {}}

    if any(
        phrase in text
        for phrase in (
            "google calendar",
            "export to calendar",
            "export tasks",
            "sync tasks to calendar",
            "send tasks to calendar",
        )
    ):
        return {"action_name": "export_tasks_to_google_calendar", "payload": {}}

    if re.search(r"\b(list|show|what are)\b.*\btasks\b", text) or text in ("tasks", "my tasks"):
        return {"action_name": "list_tasks", "payload": {}}

    if re.search(r"\b(clear|delete all|remove all)\b.*\btasks\b", text):
        return {"action_name": "delete_all_tasks", "payload": {}}

    # Add/create before done matcher — "finish" appears often in task titles
    add_match = re.search(r"\b(add|create)\b(?:\s+a)?\s+task[:\s]+(.+)$", text)
    if add_match:
        return {"action_name": "create_tasks", "payload": {"text": add_match.group(2).strip()}}

    if text.startswith("add ") or text.startswith("create "):
        stripped = re.sub(r"^(add|create)\s+", "", message.strip(), flags=re.IGNORECASE)
        return {"action_name": "create_tasks", "payload": {"text": stripped}}

    delete_match = re.search(r"\b(delete|remove)\b(?:\s+the)?\s+(.+?)(?:\s+task)?$", text)
    if delete_match:
        return {"action_name": "delete_task", "payload": {"reference": delete_match.group(2).strip()}}

    done_match = re.search(
        r"\b(?:mark|complete)\b(?:\s+the)?\s+(.+?)(?:\s+as\s+done)?$|\bfinish\b(?:\s+the)?\s+(.+?)\s+task",
        text,
    )
    if done_match:
        ref = (done_match.group(1) or done_match.group(2) or "").strip()
        if ref:
            return {"action_name": "mark_task_done", "payload": {"reference": ref}}

    return None
