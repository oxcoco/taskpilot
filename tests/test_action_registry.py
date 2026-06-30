"""Tests for the action registry."""

import pytest

from taskpilot.actions.registry import get_registry
from taskpilot.skills.deadline_check import get_deadline_summary
from taskpilot.mcp.todo_server import create_task


def test_all_mutating_actions_require_approval():
    registry = get_registry()
    mutating = [s for s in registry.all_specs() if s.category == "mutate"]
    assert len(mutating) >= 7
    for spec in mutating:
        assert spec.requires_approval is True


def test_google_calendar_export_is_registered_and_protected():
    registry = get_registry()
    spec = registry.get("export_tasks_to_google_calendar")
    assert spec.category == "mutate"
    assert spec.requires_approval is True


def test_read_actions_do_not_require_approval():
    registry = get_registry()
    for spec in registry.all_specs():
        if spec.category == "read":
            assert spec.requires_approval is False


def test_check_deadlines_returns_structure():
    create_task(title="Due soon", deadline="tomorrow")
    result = get_registry().execute("check_deadlines", {})
    assert "overdue" in result
    assert "upcoming" in result
    assert "completed" in result


def test_get_deadline_summary_matches_registry():
    summary = get_deadline_summary()
    registry_result = get_registry().execute("check_deadlines", {})
    assert summary.keys() == registry_result.keys()
