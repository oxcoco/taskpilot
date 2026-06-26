import datetime
from ..database.db import list_tasks
from ..database.models import Task

def check_deadlines() -> None:
    """Print tasks whose deadline is before today and upcoming tasks for the next 7 days.

    The function fetches all tasks, parses their deadline strings (ISO format or
    simple words like 'today'/'tomorrow'), and prints any tasks that are overdue
    or due within the next week.
    It is intended to be used from the interactive UI as a quick status check.
    """
    today = datetime.date.today()
    next_week = today + datetime.timedelta(days=3)
    overdue = []
    upcoming = []

    for task in list_tasks():
        if not task.deadline:
            continue
        # Try ISO date first
        try:
            deadline_date = datetime.datetime.strptime(task.deadline, "%Y-%m-%d").date()
        except ValueError:
            # Handle simple words
            word = task.deadline.lower()
            if word == "today":
                deadline_date = today
            elif word == "tomorrow":
                deadline_date = today + datetime.timedelta(days=1)
            else:
                # Unrecognized format – skip
                continue
        
        if deadline_date < today:
            overdue.append(task)
        elif today <= deadline_date <= next_week:
            upcoming.append(task)

    if overdue:
        print("[DeadlineCheck] Overdue tasks:")
        for t in overdue:
            print(f"  - {t.title} (ID: {t.id}) deadline: {t.deadline}")
    else:
        print("[DeadlineCheck] No overdue tasks.")

    if upcoming:
        print("[DeadlineCheck] Upcoming tasks (next 7 days):")
        for t in upcoming:
            print(f"  - {t.title} (ID: {t.id}) deadline: {t.deadline}")
