import datetime
from typing import List

from ..database.db import list_tasks
from ..database.models import Task


def _group_tasks_by_day(tasks: List[Task]) -> dict:
    """Group tasks into weekdays (Mon‑Sun) based on their deadline.

    - If a task has an ISO date deadline, it is assigned to that day if within the next 7 days.
    - If the deadline is a simple word like "today"/"tomorrow", it is mapped accordingly.
    - Otherwise, tasks without a concrete deadline are placed under "No specific day".
    Returns a dict mapping weekday names (e.g., "Monday") to a list of task titles.
    """
    today = datetime.date.today()
    week_map = {i: (today + datetime.timedelta(days=i)).strftime("%A") for i in range(7)}
    grouped = {day: [] for day in week_map.values()}
    grouped["No specific day"] = []
    for task in tasks:
        if not task.deadline:
            grouped["No specific day"].append(task.title)
            continue
        # Try ISO date first
        try:
            d = datetime.datetime.strptime(task.deadline, "%Y-%m-%d").date()
        except Exception:
            w = task.deadline.lower()
            if w == "today":
                d = today
            elif w == "tomorrow":
                d = today + datetime.timedelta(days=1)
            else:
                grouped["No specific day"].append(task.title)
                continue
        delta = (d - today).days
        if 0 <= delta < 7:
            weekday = week_map[delta]
            grouped[weekday].append(task.title)
        else:
            grouped["No specific day"].append(task.title)
    return grouped


def generate_weekly_plan() -> str:
    """Generate a simple textual weekly plan.

    The function fetches all tasks, groups them by the upcoming week, and
    returns a formatted string that can be displayed to the user. The logic is
    deterministic and does not require an external LLM, but the docstring notes
    that a real implementation could call a local Llama model to produce more
    natural language.
    """
    tasks = list_tasks()
    grouped = _group_tasks_by_day(tasks)
    lines = ["=== Weekly Plan ==="]
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        entries = grouped.get(day, [])
        if entries:
            lines.append(f"{day}:")
            for t in entries:
                lines.append(f"  - {t}")
    # Add tasks without a concrete day at the end
    misc = grouped.get("No specific day", [])
    if misc:
        lines.append("Other tasks (no specific day):")
        for t in misc:
            lines.append(f"  - {t}")
    return "\n".join(lines)
