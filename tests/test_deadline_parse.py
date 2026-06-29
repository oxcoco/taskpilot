"""Tests for deadline parsing."""

import datetime

from taskpilot.agents.deadline_parse import normalize_deadline, parse_title_and_deadline
from taskpilot.agents.task_agent import TaskAgent


def test_parse_by_weekday():
    title, deadline = parse_title_and_deadline("Finish report by Friday")
    assert title == "Finish report"
    assert deadline is not None
    assert datetime.datetime.strptime(deadline, "%Y-%m-%d")


def test_parse_next_weekday():
    title, deadline = parse_title_and_deadline("Chemistry lab by next tuesday")
    assert title == "Chemistry lab"
    today = datetime.date.today()
    parsed = datetime.datetime.strptime(deadline, "%Y-%m-%d").date()
    assert parsed > today


def test_parse_iso_deadline():
    title, deadline = parse_title_and_deadline("Submit essay by 2026-07-01")
    assert title == "Submit essay"
    assert deadline == "2026-07-01"


def test_parse_due_on_phrase():
    title, deadline = parse_title_and_deadline("Read chapter due on tomorrow")
    assert title == "Read chapter"
    assert deadline == (datetime.date.today() + datetime.timedelta(days=1)).isoformat()


def test_parse_strips_time_suffix():
    title, deadline = parse_title_and_deadline("Finish chemistry project by Friday at 5pm")
    assert title == "Finish chemistry project"
    assert deadline is not None


def test_extract_tasks_multiword_deadline():
    tasks = TaskAgent().extract_tasks("Finish OS project by next Friday")
    assert len(tasks) == 1
    assert tasks[0].title == "Finish OS project"
    assert tasks[0].deadline is not None
    assert datetime.datetime.strptime(tasks[0].deadline, "%Y-%m-%d")


def test_normalize_us_date():
    result = normalize_deadline("7/3/2026")
    assert result == "2026-07-03"
