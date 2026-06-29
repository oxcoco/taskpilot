"""Resolve user references to task IDs."""

from __future__ import annotations

import re
from typing import List

from ..agents.task_agent import TaskAgent


def resolve_task_reference(reference: str, tasks: List[dict] | None = None) -> str | None:
    """Resolve a task reference (index, UUID, or fuzzy title) to a task ID.

    Returns None if ambiguous or not found.
    """
    reference = reference.strip()
    if not reference:
        return None

    all_tasks = tasks if tasks is not None else [t.to_dict() for t in TaskAgent.list_tasks()]
    if not all_tasks:
        return None

    # Numeric index (1-based, as shown in CLI)
    if reference.isdigit():
        idx = int(reference)
        if 1 <= idx <= len(all_tasks):
            return all_tasks[idx - 1]["id"]
        return None

    # Exact UUID match
    for task in all_tasks:
        if task["id"] == reference:
            return task["id"]

    # Fuzzy title match (case-insensitive substring)
    ref_lower = reference.lower()
    matches = [t for t in all_tasks if ref_lower in t["title"].lower()]
    if len(matches) == 1:
        return matches[0]["id"]

    # Try stripping common prefixes like "the" / "task"
    cleaned = re.sub(r"^(the|task)\s+", "", ref_lower, flags=re.IGNORECASE).strip()
    if cleaned != ref_lower:
        matches = [t for t in all_tasks if cleaned in t["title"].lower()]
        if len(matches) == 1:
            return matches[0]["id"]

    return None


def find_ambiguous_matches(reference: str) -> list[dict]:
    """Return multiple tasks matching a reference (for disambiguation prompts)."""
    all_tasks = [t.to_dict() for t in TaskAgent.list_tasks()]
    ref_lower = reference.lower().strip()
    return [t for t in all_tasks if ref_lower in t["title"].lower()]
