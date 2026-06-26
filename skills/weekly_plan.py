import datetime
import os
from typing import List

from dotenv import load_dotenv
import openai

from ..database.db import list_tasks
from ..database.models import Task, TaskStatus


# Load environment variables from .env file located at project root
def _load_openai_key() -> str:
    """Load OPENAI_API_KEY from a .env file.

    Returns the API key as a string. Raises a RuntimeError if the key is not
    found, guiding the user to create a .env file based on .env.example.
    """
    # Load .env from the project root (search upwards automatically)
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not found after loading .env. Verify the key is set in the .env file at the project root."
        )
    return api_key


def _group_tasks_by_day(tasks: List[Task]) -> dict:
    """Group tasks into weekdays (Mon‑Sun) based on their deadline.

    - If a task has an ISO date deadline, it is assigned to that day if within the next 7 days.
    - If the deadline is a simple word like "today"/"tomorrow", it is mapped accordingly.
    - Otherwise, tasks without a concrete deadline are placed under "No specific day".
    Returns a dict mapping weekday names (e.g., "Monday") to a list of task titles.
    """
    today = datetime.date.today()
    week_map = {
        i: (today + datetime.timedelta(days=i)).strftime("%A") for i in range(7)
    }
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


def _format_tasks_for_prompt(tasks: List[Task]) -> str:
    """Create a concise markdown‑style representation of tasks for the LLM.

    Each line includes title, deadline (ISO or natural word), priority, estimated hours, and status.
    """
    lines = []
    for t in tasks:
        deadline = t.deadline or "No deadline"
        status = t.status.value if hasattr(t, "status") else "UNKNOWN"
        lines.append(
            f"- **{t.title}** (deadline: {deadline}, priority: {t.priority.name}, hours: {t.estimated_hours}, status: {status})"
        )
    return "\n".join(lines)


def generate_weekly_plan() -> str:
    """Generate a textual weekly plan using the OpenAI LLM.

    The function:
    1. Loads all tasks from the DB.
    2. Formats them into a prompt describing their traits.
    3. Calls the OpenAI Chat Completion API (gpt-4o by default).
    4. Returns the model's response as a plain string.
    """
    # Ensure we have an API key
    api_key = _load_openai_key()
    # The OpenAI client reads the key from the environment automatically
    client = openai.OpenAI()

    # Load tasks and exclude completed ones
    all_tasks = list_tasks()
    tasks = [t for t in all_tasks if t.status != TaskStatus.COMPLETED]

    # Add today's date (ISO) for the LLM context
    today_iso = datetime.date.today().isoformat()

    # Build prompt with date and ordering suggestions
    prompt = (
        f"You are a personal productivity assistant. Today is {today_iso}. "
        "Based on the list of tasks below, create a concise, friendly weekly plan for the next 7 days. "
        "Group tasks by the day they should be worked on, taking into account their deadlines, priorities (HIGH > MEDIUM > LOW), and estimated hours. "
        "Do not assign specific weekday names (Monday, Tuesday, etc.) unless the task deadline explicitly falls on that day; otherwise refer to dates or say 'Day X'. "
        "If a task has no specific deadline, place it under an 'Other' section. Additionally, suggest which tasks to tackle first each day, especially when multiple tasks are present. "
        "Tasks marked as COMPLETED are already done and should not be scheduled again. "
        "\n\nTasks:\n" + _format_tasks_for_prompt(tasks)
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates weekly plans.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        plan = response.choices[0].message.content.strip()
        return plan
    except Exception as e:
        # Fallback to deterministic plan if the API fails
        return f"Error generating plan via OpenAI: {e}\n\n" + _fallback_plan(tasks)

    def _fallback_plan(tasks: List[Task]) -> str:
        """Deterministic plain‑text fallback plan (same logic as earlier version)."""
        grouped = _group_tasks_by_day(tasks)
        today = datetime.date.today()
        # Build mapping of weekday names to ISO dates for the next 7 days
        week_dates = {
            (today + datetime.timedelta(days=i))
            .strftime("%A"): (today + datetime.timedelta(days=i))
            .isoformat()
            for i in range(7)
        }
        lines = ["=== Weekly Plan ==="]
        for day in [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]:
            entries = grouped.get(day, [])
            if entries:
                date_iso = week_dates.get(day, "")
                header = f"{day} ({date_iso})" if date_iso else day
                lines.append(header + ":")
                for t in entries:
                    lines.append(f"  - {t}")
        misc = grouped.get("No specific day", [])
        if misc:
            lines.append("Other tasks (no specific day):")
            for t in misc:
                lines.append(f"  - {t}")
        return "\n".join(lines)


__all__ = ["generate_weekly_plan"]
