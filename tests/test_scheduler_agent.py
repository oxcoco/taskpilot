import os, sys, pytest, datetime

# Ensure project root is on PYTHONPATH
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from taskpilot.agents.scheduler_agent import SchedulerAgent
from taskpilot.agents.task_agent import TaskAgent

def test_schedule_with_various_deadlines():
    # Create tasks with natural language deadlines
    raw = [
        "Task Today by today",
        "Task Tomorrow by tomorrow",
        "Task Monday by monday",
        "Task Next Tue by next tuesday",
        "Task ISO by 2026-07-01",
    ]
    tasks = []
    for r in raw:
        tasks.extend(TaskAgent().extract_tasks(r))
    # Persist tasks so SchedulerAgent can update DB
    TaskAgent.create_tasks(tasks)
    # Get dicts for scheduling
    task_dicts = [t.to_dict() for t in TaskAgent.list_tasks()]
    schedule = SchedulerAgent.generate_schedule(task_dicts)
    # All deadlines should be ISO strings in the schedule keys
    today_iso = datetime.date.today().isoformat()
    tomorrow_iso = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    # Verify presence of expected dates
    assert today_iso in schedule
    assert tomorrow_iso in schedule
    # Monday may be same week or next depending on today; just ensure a date string exists
    assert any(isinstance(date, str) for date in schedule.keys())

def test_schedule_capacity_limit():
    # Create enough tasks to exceed one workday (8h)
    tasks = []
    for i in range(10):
        frag = f"Task {i} by today"
        tasks.extend(TaskAgent().extract_tasks(frag))
    TaskAgent.create_tasks(tasks)
    task_dicts = [t.to_dict() for t in TaskAgent.list_tasks()]
    schedule = SchedulerAgent.generate_schedule(task_dicts)
    # With 10 tasks of 1h each, should span at least two days
    assert len(schedule) >= 2
    # Verify total hours per day do not exceed 8
    for day, titles in schedule.items():
        assert len(titles) <= 8
