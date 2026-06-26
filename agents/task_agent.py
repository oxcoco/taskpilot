# taskpilot/agents/task_agent.py
"""TaskAgent – extracts structured tasks from natural language.

Now returns :class:`taskpilot.database.models.Task` instances instead of raw
dictionaries, matching the expectations of the CoordinatorAgent.
"""

from __future__ import annotations

import re
import uuid
from typing import List

from ..database.models import Task, TaskPriority, TaskStatus


class TaskAgent:
    """Parse free‑form text into :class:`Task` objects.

    Simple heuristic:
    * Split on punctuation or the word ``and``.
    * Detect a trailing ``by <deadline>`` phrase.
    * Generate a UUID for each task.
    * Populate default values for other fields; priority will be set later.
    """

    @staticmethod
    def _parse_fragment(fragment: str) -> Task:
        fragment = fragment.strip()
        # Detect "by <deadline>" at the end.
        match = re.search(r"(?P<title>.+?)\s+by\s+(?P<deadline>\w+)$", fragment, flags=re.IGNORECASE)
        if match:
            title = match.group("title").strip()
            deadline = match.group("deadline").strip()
        else:
            title = fragment
            deadline = None
        return Task(
            id=str(uuid.uuid4()),
            title=title,
            description="",
            deadline=deadline,
            priority=TaskPriority.MEDIUM,
            estimated_hours=1.0,
            status=TaskStatus.PENDING,
        )

    def extract_tasks(self, text: str) -> List[Task]:
        """Extract a list of :class:`Task` objects from *text*.

        The text may contain multiple sentences separated by punctuation or the
        conjunction ``and``. Each fragment is parsed independently.
        """
        fragments = re.split(r"[.;\n]+|\band\b", text, flags=re.IGNORECASE)
        tasks: List[Task] = []
        for frag in fragments:
            if frag.strip():
                tasks.append(self._parse_fragment(frag))
        return tasks

