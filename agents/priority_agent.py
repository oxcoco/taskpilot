# taskpilot/agents/priority_agent.py
"""PriorityAgent – assigns a priority level to each task.

The logic follows the specification:
* **HIGH** – deadline within 2 days
* **MEDIUM** – deadline within 7 days
* **LOW** – otherwise or no deadline

The implementation parses simple English day names (e.g., "Friday") and
relative terms like "today" or "tomorrow". It does not depend on any external
libraries beyond the Python standard library.
"""

import datetime
from typing import List, Dict
from .task_agent import TaskAgent  # noqa: F401  (imported for type hint consistency)
from ..database.models import TaskPriority


def _parse_deadline_word(word: str) -> datetime.date | None:
    """Convert a single word deadline into a concrete date.

    Supported words:
    * "today"
    * "tomorrow"
    * weekday names ("monday" … "sunday") – interpreted as the next
      occurrence of that weekday (including today if it matches).
    Returns ``None`` for unrecognised words.
    """
    today = datetime.date.today()
    w = word.lower()
    if w == "today":
        return today
    if w == "tomorrow":
        return today + datetime.timedelta(days=1)
    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    if w in weekdays:
        target = weekdays[w]
        days_ahead = (target - today.weekday()) % 7
        # If today is the same weekday, treat it as today.
        return today + datetime.timedelta(days=days_ahead)
    return None


class PriorityAgent:
    """Assign priority to a list of task dictionaries.

    The input format matches the output of :class:`TaskAgent` – each task is a
    ``dict`` with at least ``title`` and optional ``deadline`` (a string).
    The method returns a new list where each dict also contains the key
    ``priority`` with a value from :class:`TaskPriority`.
    """

    @staticmethod
    def rank_tasks(tasks: List[Dict[str, str | None]]) -> List[Dict[str, str | None]]:
        ranked: List[Dict[str, str | None]] = []
        for task in tasks:
            deadline_str = task.get("deadline")
            priority = TaskPriority.LOW
            if deadline_str:
                # Try to extract a single word deadline.
                # Simple heuristic: take the last word after "by" if present.
                # The TaskAgent already stripped the "by <word>" from the title,
                # leaving the word as the deadline value.
                deadline_date = _parse_deadline_word(deadline_str)
                if deadline_date:
                    days_until = (deadline_date - datetime.date.today()).days
                    if days_until <= 2:
                        priority = TaskPriority.HIGH
                    elif days_until <= 7:
                        priority = TaskPriority.MEDIUM
                    else:
                        priority = TaskPriority.LOW
                else:
                    # Unrecognised deadline – keep LOW.
                    priority = TaskPriority.LOW
            task_copy = dict(task)
            task_copy["priority"] = priority.value
            ranked.append(task_copy)
        # Sort by priority: HIGH > MEDIUM > LOW
        order = {TaskPriority.HIGH.value: 0, TaskPriority.MEDIUM.value: 1, TaskPriority.LOW.value: 2}
        ranked.sort(key=lambda t: order.get(t.get("priority"), 3))
        return ranked
