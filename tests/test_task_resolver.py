"""Tests for task reference resolution."""

from taskpilot.actions.task_resolver import resolve_task_reference
from taskpilot.mcp.todo_server import create_task


def test_resolve_by_index():
    create_task(title="Alpha task")
    create_task(title="Beta task")
    tasks = [{"id": "a", "title": "Alpha task"}, {"id": "b", "title": "Beta task"}]
    assert resolve_task_reference("1", tasks) == "a"
    assert resolve_task_reference("2", tasks) == "b"


def test_resolve_by_title_fragment():
    tasks = [{"id": "x", "title": "Chemistry homework"}]
    assert resolve_task_reference("chemistry", tasks) == "x"


def test_ambiguous_returns_none():
    tasks = [
        {"id": "1", "title": "Math report"},
        {"id": "2", "title": "Math quiz"},
    ]
    assert resolve_task_reference("math", tasks) is None
