"""Tests for the approval gate."""

import pytest

from taskpilot.actions.registry import get_registry
from taskpilot.approval.gate import ApprovalGate
from taskpilot.approval.models import ApprovalStatus
from taskpilot.approval.store import get_store
from taskpilot.agents.task_agent import TaskAgent
from taskpilot.database.models import TaskPriority, TaskStatus
from taskpilot.mcp.todo_server import create_task


@pytest.fixture(autouse=True)
def clear_approval_store():
    get_store().clear()
    yield
    get_store().clear()


def test_mutating_action_requires_staging():
    gate = ApprovalGate()
    pending = gate.stage("sess-1", "create_tasks", {"text": "Finish report by Friday"})
    assert pending.status == ApprovalStatus.PENDING
    assert pending.action_name == "create_tasks"
    assert "Finish report" in pending.summary


def test_cannot_execute_mutating_action_directly():
    registry = get_registry()
    with pytest.raises(PermissionError):
        registry.execute("create_tasks", {"text": "Test task"})


def test_approve_creates_task():
    gate = ApprovalGate()
    pending = gate.stage("sess-1", "create_tasks", {"text": "Approved task by tomorrow"})
    executed = gate.approve("sess-1", pending.id)
    assert executed.status == ApprovalStatus.EXECUTED
    tasks = TaskAgent.list_tasks()
    assert any("Approved task" in t.title for t in tasks)


def test_reject_does_not_create_task():
    gate = ApprovalGate()
    pending = gate.stage("sess-1", "create_tasks", {"text": "Rejected task by tomorrow"})
    rejected = gate.reject("sess-1", pending.id)
    assert rejected.status == ApprovalStatus.REJECTED
    tasks = TaskAgent.list_tasks()
    assert not any("Rejected task" in t.title for t in tasks)


def test_approve_wrong_session_raises():
    gate = ApprovalGate()
    pending = gate.stage("sess-1", "create_tasks", {"text": "Secret task"})
    with pytest.raises(PermissionError):
        gate.approve("sess-2", pending.id)


def test_delete_task_requires_approval():
    task = create_task(title="To delete", priority=TaskPriority.MEDIUM.value)
    gate = ApprovalGate()
    pending = gate.stage("sess-1", "delete_task", {"task_id": task.id})
    gate.approve("sess-1", pending.id)
    assert TaskAgent.get_task(task.id) is None


def test_google_calendar_export_requires_approval(monkeypatch):
    from taskpilot.actions import schedule_actions

    task = create_task(title="Export me", deadline="tomorrow", priority=TaskPriority.HIGH.value)

    class FakeClient:
        def __init__(self) -> None:
            self.calls = []

        def export_tasks(self, tasks, include_completed=False, include_undated=False):
            self.calls.append(
                {
                    "tasks": list(tasks),
                    "include_completed": include_completed,
                    "include_undated": include_undated,
                }
            )
            return {
                "calendar_id": "primary",
                "timezone": "UTC",
                "exported_count": len(self.calls[-1]["tasks"]),
                "skipped_count": 0,
                "created_events": [{"id": "evt-1", "title": task.title}],
                "skipped_tasks": [],
            }

    fake_client = FakeClient()
    monkeypatch.setattr(schedule_actions.GoogleCalendarClient, "from_environment", classmethod(lambda cls, **kwargs: fake_client))

    gate = ApprovalGate()
    pending = gate.stage("sess-1", "export_tasks_to_google_calendar", {})
    assert pending.action_name == "export_tasks_to_google_calendar"
    assert "Google Calendar" in pending.summary

    executed = gate.approve("sess-1", pending.id)
    assert executed.status == ApprovalStatus.EXECUTED
    assert executed.result["exported_count"] == 1
    assert fake_client.calls


def test_google_calendar_export_rejects_without_export(monkeypatch):
    from taskpilot.actions import schedule_actions

    class FakeClient:
        def export_tasks(self, *args, **kwargs):
            raise AssertionError("export should not be called on reject")

    monkeypatch.setattr(schedule_actions.GoogleCalendarClient, "from_environment", classmethod(lambda cls, **kwargs: FakeClient()))

    gate = ApprovalGate()
    pending = gate.stage("sess-1", "export_tasks_to_google_calendar", {})
    rejected = gate.reject("sess-1", pending.id)
    assert rejected.status == ApprovalStatus.REJECTED
