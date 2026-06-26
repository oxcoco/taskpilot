import os, sys, pytest

# Ensure project root is on PYTHONPATH
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from taskpilot.agents.task_agent import TaskAgent
from taskpilot.database.models import TaskPriority, TaskStatus

def test_create_and_get_task():
    # Create a task via UI helper (which uses TaskAgent internally)
    TaskAgent.create_tasks([TaskAgent()._parse_fragment("Buy milk by today")])
    tasks = TaskAgent.list_tasks()
    assert len(tasks) == 1
    task = tasks[0]
    assert task.title == "Buy milk"
    # Deadline should be ISO today
    assert task.deadline == __import__('datetime').date.today().isoformat()
    # Retrieve by id
    fetched = TaskAgent.get_task(task.id)
    assert fetched.id == task.id
    assert fetched.title == task.title

def test_update_task():
    # Setup initial task
    task = TaskAgent()._parse_fragment("Write report by tomorrow")
    TaskAgent.create_tasks([task])
    # Update fields
    task.title = "Write final report"
    task.priority = TaskPriority.HIGH
    TaskAgent.update_task(task)
    updated = TaskAgent.get_task(task.id)
    assert updated.title == "Write final report"
    assert updated.priority == TaskPriority.HIGH

def test_status_transitions():
    task = TaskAgent()._parse_fragment("Read book")
    TaskAgent.create_tasks([task])
    # Mark completed
    TaskAgent.set_status(task.id, TaskStatus.COMPLETED)
    completed = TaskAgent.get_task(task.id)
    assert completed.status == TaskStatus.COMPLETED
    # Mark pending again
    TaskAgent.set_status(task.id, TaskStatus.PENDING)
    pending = TaskAgent.get_task(task.id)
    assert pending.status == TaskStatus.PENDING

def test_delete_task():
    task = TaskAgent()._parse_fragment("Delete me")
    TaskAgent.create_tasks([task])
    TaskAgent.delete_task(task.id)
    assert TaskAgent.get_task(task.id) is None
