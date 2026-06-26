# taskpilot/agents/scheduler_agent.py
"""SchedulerAgent – creates a simple daily schedule.

The schedule is a mapping from a date string (YYYY‑MM‑DD) to a list of task
titles.  Workdays are fixed to 09:00–17:00 (8 hours).  Each task is assumed to
require ``estimated_hours`` (default 1 hour if not provided).

The algorithm is straightforward:
1. Iterate over the tasks in priority order (high → low).
2. Fill the current day until the 8‑hour limit is reached.
3. When the limit is exceeded, start a new day.

The result is returned as a ``dict`` that callers can render as they wish.
"""

import datetime
from datetime import time
from typing import List, Dict, Any, Optional

from ..mcp.calendar_server import create_event


class SchedulerAgent:
    """Generate a week‑long schedule from a list of task dictionaries.

    Expected input format (as produced by ``PriorityAgent``)::

        [{"title": "Write report", "deadline": "Friday", "priority": "HIGH", "estimated_hours": 2}, ...]

    Only ``title`` and ``estimated_hours`` are required for scheduling; missing
    ``estimated_hours`` defaults to ``1.0``.
    """

    WORKDAY_HOURS = 8

    @staticmethod
    def generate_schedule(tasks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Generate a schedule respecting deadlines and daily capacity.

        Tasks are assumed to be ordered by priority (high → low). The function
        first schedules tasks that have a concrete deadline, placing them on the
        specified day or the next available day if the day is full. After all
        deadline‑bound tasks are placed, remaining tasks without a deadline are
        scheduled sequentially starting from the earliest day that still has
        free capacity.
        """
        schedule: Dict[str, List[str]] = {}
        # Track used hours per concrete date
        hours_used: Dict[datetime.date, float] = {}
        today = datetime.date.today()

        def parse_deadline(word: Optional[str]) -> datetime.date:
            """Convert a deadline word (or ISO date) to a concrete date.

            Handles ISO dates (YYYY-MM-DD), "today", "tomorrow", weekday names
            (e.g., "monday"), and phrases like "next monday".
            """
            today = datetime.date.today()
            if not word:
                return today
            # Try ISO date first (YYYY-MM-DD)
            try:
                return datetime.datetime.strptime(word, "%Y-%m-%d").date()
            except Exception:
                pass
            w = word.lower().strip()
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
            # Direct weekday name (e.g., "monday")
            if w in weekdays:
                target = weekdays[w]
                days_ahead = (target - today.weekday()) % 7
                return today + datetime.timedelta(days_ahead)
            # "next <weekday>" handling
            if w.startswith("next "):
                day_name = w.split(" ", 1)[1]
                if day_name in weekdays:
                    target = weekdays[day_name]
                    days_ahead = (target - today.weekday()) % 7
                    days_ahead = days_ahead or 7
                    return today + datetime.timedelta(days_ahead)
            # Fallback
            return today

        def find_day(start: datetime.date, est: float) -> datetime.date:
            """Return the first day on or after *start* with enough free hours."""
            day = start
            while True:
                used = hours_used.get(day, 0.0)
                if used + est <= SchedulerAgent.WORKDAY_HOURS:
                    return day
                day += datetime.timedelta(days=1)

        # First schedule tasks with deadlines
        latest_day = today
        for task in tasks:
            deadline = task.get("deadline")
            if not deadline:
                continue
            est = float(task.get("estimated_hours", 1.0))
            target = parse_deadline(deadline)
            # Convert deadline to ISO string for storage/display
            iso_deadline = target.isoformat()
            task["deadline"] = iso_deadline
            # Persist updated deadline back to DB
            try:
                from ..agents.task_agent import TaskAgent
                from ..database.models import Task
                updated_task = Task(**task)
                TaskAgent.update_task(updated_task)
            except Exception:
                pass

            day = find_day(target, est)
            schedule.setdefault(day.isoformat(), []).append(task["title"])
            hours_used[day] = hours_used.get(day, 0.0) + est
            if day > latest_day:
                latest_day = day

        # Then schedule tasks without deadlines
        next_day = latest_day
        for task in tasks:
            if task.get("deadline"):
                continue
            est = float(task.get("estimated_hours", 1.0))
            day = find_day(next_day, est)
            schedule.setdefault(day.isoformat(), []).append(task["title"])
            hours_used[day] = hours_used.get(day, 0.0) + est
            next_day = day
        SchedulerAgent._persist_schedule(schedule)
        return schedule

    @staticmethod
    def _persist_schedule(schedule: Dict[str, List[str]]) -> None:
        """Create calendar events for each scheduled task.

        For each date, each task title gets a placeholder event from 09:00 to 17:00.
        """
        for date_str, titles in schedule.items():
            try:
                day_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            except Exception:
                continue
            for title in titles:
                start_dt = datetime.datetime.combine(day_date, time(hour=9))
                end_dt = datetime.datetime.combine(day_date, time(hour=17))
                try:
                    create_event(title=title, start=start_dt, end=end_dt)
                except Exception:
                    # Ignore failures to keep scheduler robust
                    pass
