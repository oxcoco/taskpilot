import os, sys

sys.path.append(os.getcwd())
from taskpilot.agents.scheduler_agent import SchedulerAgent

tasks = [
    {"title": "Task Today", "deadline": "today", "estimated_hours": 2},
    {"title": "Task Tomorrow", "deadline": "tomorrow", "estimated_hours": 2},
    {"title": "Task Monday", "deadline": "monday", "estimated_hours": 2},
    {"title": "Task Next Tuesday", "deadline": "next tuesday", "estimated_hours": 2},
    {"title": "Task ISO", "deadline": "2026-07-01", "estimated_hours": 2},
]

schedule = SchedulerAgent.generate_schedule(tasks)
print(schedule)
