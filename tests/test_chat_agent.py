"""Tests for ChatAgent with rule-based fallback."""

import pytest

from taskpilot.agents.chat_agent import ChatAgent
from taskpilot.agents.chat_session import get_session_store
from taskpilot.approval.store import get_store
from taskpilot.agents.task_agent import TaskAgent


@pytest.fixture(autouse=True)
def clear_stores():
    get_store().clear()
    get_session_store().clear()
    yield
    get_store().clear()
    get_session_store().clear()


def test_rule_fallback_check_deadlines():
    agent = ChatAgent()
    response = agent._process_with_rules(
        agent.sessions.create(),
        "What deadlines are coming up?",
    )
    assert response["approval_required"] is False
    assert response["artifacts"]["type"] == "deadline_summary"


def test_rule_fallback_create_stages_approval():
    agent = ChatAgent()
    session = agent.sessions.create()
    response = agent._process_with_rules(session, "add finish report by Friday")
    assert response["approval_required"] is True
    assert response["message"] == ""
    assert response["pending_action"]["action_name"] == "create_tasks"


def test_approve_flow_via_agent():
    agent = ChatAgent()
    session = agent.sessions.create()
    staged = agent._process_with_rules(session, "add approved item by tomorrow")
    assert staged["approval_required"] is True
    pending_id = staged["pending_action"]["id"]
    session_id = session.id

    result = agent.approve(session_id, pending_id)
    assert "created" in result["message"].lower()
    tasks = TaskAgent.list_tasks()
    assert any("approved item" in t.title.lower() for t in tasks)


def test_reject_flow_via_agent():
    agent = ChatAgent()
    session = agent.sessions.create()
    staged = agent._process_with_rules(session, "add rejected item by tomorrow")
    assert staged["approval_required"] is True
    pending_id = staged["pending_action"]["id"]
    session_id = session.id

    agent.reject(session_id, pending_id)
    tasks = TaskAgent.list_tasks()
    assert not any("rejected item" in t.title.lower() for t in tasks)
