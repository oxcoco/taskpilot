"""ChatAgent – conversational interface with tool calling and approval gating."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

from ..actions.registry import get_registry
from ..actions.task_resolver import find_ambiguous_matches, resolve_task_reference
from ..agents.deadline_parse import normalize_deadline
from ..approval.gate import ApprovalGate
from ..approval.models import PendingAction
from .chat_session import ChatSession, get_session_store
from .intent_router import route_message

SYSTEM_PROMPT = """You are TaskPilot's assistant. You help users manage tasks and schedules.

Rules:
- Use tools for factual data; never invent tasks or deadlines.
- For create, update, delete, status changes, or persisting schedules, call the matching tool directly.
  Do NOT ask the user to confirm in your reply — the UI approval card handles confirmation.
- For deadline questions, use check_deadlines.
- For planning questions, use generate_weekly_plan or get_schedule.
- For calendar export requests, use export_tasks_to_google_calendar and require approval before exporting.
- Be concise. If a task reference is ambiguous, ask the user to clarify instead of guessing.

Creating tasks with deadlines:
- ALWAYS prefer create_tasks with separate `title` and `deadline` fields.
- Put only the task name in `title` (e.g. "Chemistry lab report"), never "by Friday" in title.
- Put the due date in `deadline` using: today, tomorrow, friday, next monday, 2026-07-03, or 7/3/2026.
- Example: user says "Add chemistry homework due next Friday" → title="Chemistry homework", deadline="next friday".
- Use `text` only for a single free-form sentence when splitting title/deadline is awkward.

Updating deadlines:
- Use update_task with `reference` plus a normalized `deadline` value in the same formats above.
"""


class ChatAgent:
    """Orchestrates chat: LLM tool calling, rule fallback, and approval staging."""

    def __init__(self) -> None:
        self.registry = get_registry()
        self.approval = ApprovalGate(self.registry)
        self.sessions = get_session_store()

    def handle_message(self, message: str, session_id: str | None = None) -> dict[str, Any]:
        session = self.sessions.get_or_create(session_id)
        session.add_message("user", message)

        try:
            response = self._process_with_llm(session, message)
        except Exception:
            response = self._process_with_rules(session, message)

        if response.get("message"):
            session.add_message("assistant", response["message"])
        response["session_id"] = session.id
        return response

    def approve(self, session_id: str, pending_action_id: str) -> dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session:
            raise KeyError("Session not found")

        action = self.approval.approve(session_id, pending_action_id)
        message = self._format_execution_message(action)
        session.add_message("assistant", message)
        return {
            "session_id": session_id,
            "message": message,
            "approval_required": False,
            "pending_action": None,
            "artifacts": self._artifacts_from_result(action),
            "executed_action": action.to_dict(),
        }

    def reject(self, session_id: str, pending_action_id: str) -> dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session:
            raise KeyError("Session not found")

        action = self.approval.reject(session_id, pending_action_id)
        message = "Action cancelled. Nothing was changed."
        session.add_message("assistant", message)
        return {
            "session_id": session_id,
            "message": message,
            "approval_required": False,
            "pending_action": None,
            "artifacts": None,
            "executed_action": action.to_dict(),
        }

    def list_pending(self, session_id: str) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self.approval.list_pending(session_id)]

    def get_history(self, session_id: str) -> list[dict[str, Any]]:
        session = self.sessions.get(session_id)
        if not session:
            return []
        return [m.to_dict() for m in session.messages]

    def _process_with_llm(self, session: ChatSession, message: str) -> dict[str, Any]:
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")

        import openai

        client = openai.OpenAI()
        task_context = self._task_context_snippet()
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\nCurrent tasks:\n" + task_context},
            *session.history_for_llm(),
        ]

        tools = self.registry.openai_tools()
        tool_calls_made: list[dict[str, Any]] = []

        for _ in range(5):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.3,
            )
            choice = response.choices[0].message

            if not choice.tool_calls:
                return {
                    "message": (choice.content or "").strip() or "How can I help with your tasks?",
                    "approval_required": False,
                    "pending_action": None,
                    "artifacts": None,
                }

            messages.append(
                {
                    "role": "assistant",
                    "content": choice.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in choice.tool_calls
                    ],
                }
            )

            for tc in choice.tool_calls:
                action_name = tc.function.name
                payload = json.loads(tc.function.arguments or "{}")
                tool_result, chat_response = self._invoke_tool(session.id, action_name, payload)
                tool_calls_made.append({"action": action_name, "payload": payload, "result": tool_result})

                if chat_response.get("approval_required"):
                    return chat_response

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(tool_result, default=str),
                    }
                )

        return {
            "message": "I completed the requested actions.",
            "approval_required": False,
            "pending_action": None,
            "artifacts": self._merge_artifacts(tool_calls_made),
        }

    def _process_with_rules(self, session: ChatSession, message: str) -> dict[str, Any]:
        routed = route_message(message)
        if not routed:
            return {
                "message": (
                    "I can help you list tasks, check deadlines, generate schedules, "
                    "create tasks, and more. Try: \"What deadlines are coming up?\" or "
                    "\"Add finish report by Friday\"."
                ),
                "approval_required": False,
                "pending_action": None,
                "artifacts": None,
            }

        action_name = routed["action_name"]
        payload = routed["payload"]
        _result, chat_response = self._invoke_tool(session.id, action_name, payload)

        if chat_response.get("approval_required"):
            return chat_response

        return self._finalize_read_response(action_name, _result, chat_response.get("message"))

    def _invoke_tool(
        self, session_id: str, action_name: str, payload: dict[str, Any]
    ) -> tuple[Any, dict[str, Any]]:
        spec = self.registry.get(action_name)
        payload = self._normalize_action_payload(action_name, payload)

        # Disambiguation for reference-based mutations
        if spec.requires_approval and payload.get("reference") and not payload.get("task_id"):
            ambiguous = find_ambiguous_matches(payload["reference"])
            if len(ambiguous) > 1:
                titles = ", ".join(f"\"{t['title']}\"" for t in ambiguous[:5])
                return None, {
                    "message": f"I found multiple tasks matching \"{payload['reference']}\": {titles}. Which one did you mean?",
                    "approval_required": False,
                    "pending_action": None,
                    "artifacts": {"type": "task_list", "data": {"tasks": ambiguous}},
                }
            if len(ambiguous) == 0 and action_name in (
                "delete_task",
                "update_task",
                "mark_task_done",
                "mark_task_undone",
            ):
                resolved = resolve_task_reference(payload["reference"])
                if not resolved:
                    return None, {
                        "message": f"I couldn't find a task matching \"{payload['reference']}\".",
                        "approval_required": False,
                        "pending_action": None,
                        "artifacts": None,
                    }

        if spec.requires_approval:
            pending = self.approval.stage(session_id, action_name, payload)
            return None, self._approval_response(pending)

        result = self.registry.execute(action_name, payload)
        message = self._summarize_read_result(action_name, result)
        artifacts = self._build_artifacts(action_name, result)
        return result, {
            "message": message,
            "approval_required": False,
            "pending_action": None,
            "artifacts": artifacts,
        }

    def _approval_response(self, pending: PendingAction) -> dict[str, Any]:
        return {
            "message": "",
            "approval_required": True,
            "pending_action": {
                "id": pending.id,
                "action_name": pending.action_name,
                "summary": pending.summary,
                "details": pending.payload,
                "destructive": pending.destructive,
            },
            "artifacts": None,
        }

    def _finalize_read_response(
        self, action_name: str, result: Any, message: str | None
    ) -> dict[str, Any]:
        return {
            "message": message or self._summarize_read_result(action_name, result),
            "approval_required": False,
            "pending_action": None,
            "artifacts": self._build_artifacts(action_name, result),
        }

    def _summarize_read_result(self, action_name: str, result: Any) -> str:
        if action_name == "check_deadlines":
            overdue = len(result.get("overdue", []))
            upcoming = len(result.get("upcoming", []))
            parts = []
            if overdue:
                parts.append(f"{overdue} overdue")
            if upcoming:
                parts.append(f"{upcoming} due in the next 3 days")
            return parts and f"You have {', '.join(parts)} task(s)." or "No overdue or upcoming deadlines."
        if action_name == "list_tasks":
            tasks = result.get("tasks", result) if isinstance(result, dict) else result
            count = len(tasks) if isinstance(tasks, list) else 0
            return f"You have {count} task(s)."
        if action_name == "generate_weekly_plan":
            return "Here's your weekly plan."
        if action_name == "get_schedule":
            schedule = result.get("schedule", {})
            days = len([k for k in schedule if k != "Completed"])
            return f"Schedule preview across {days} day(s)."
        if action_name == "get_task":
            task = result.get("task", {})
            return f"Task: {task.get('title', 'unknown')}"
        return "Done."

    def _build_artifacts(self, action_name: str, result: Any) -> dict[str, Any] | None:
        spec = self.registry.get(action_name)
        if not spec.artifact_type:
            return None
        if action_name == "check_deadlines":
            return {"type": "deadline_summary", "data": result}
        if action_name == "list_tasks":
            data = result.get("tasks", result) if isinstance(result, dict) else result
            return {"type": "task_list", "data": {"tasks": data}}
        if action_name == "generate_weekly_plan":
            return {"type": "weekly_plan", "data": result}
        if action_name in ("get_schedule", "generate_and_persist_schedule"):
            return {"type": "schedule", "data": result.get("schedule", result)}
        return {"type": spec.artifact_type, "data": result}

    def _merge_artifacts(self, tool_calls: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not tool_calls:
            return None
        last = tool_calls[-1]
        return self._build_artifacts(last["action"], last.get("result"))

    def _artifacts_from_result(self, action: PendingAction) -> dict[str, Any] | None:
        if not action.result:
            return None
        return self._build_artifacts(action.action_name, action.result)

    def _format_execution_message(self, action: PendingAction) -> str:
        name = action.action_name
        if name == "create_tasks":
            count = action.result.get("count", 1) if action.result else 1
            return f"Done — created {count} task(s)."
        if name == "delete_task":
            title = action.result.get("title", "task") if action.result else "task"
            return f"Done — deleted \"{title}\"."
        if name == "delete_all_tasks":
            count = action.result.get("deleted_count", 0) if action.result else 0
            return f"Done — deleted {count} task(s)."
        if name == "update_task":
            return "Done — task updated."
        if name == "mark_task_done":
            return "Done — task marked as completed."
        if name == "mark_task_undone":
            return "Done — task marked as pending."
        if name == "generate_and_persist_schedule":
            return "Done — schedule generated and calendar events saved."
        if name == "export_tasks_to_google_calendar":
            count = action.result.get("exported_count", 0) if action.result else 0
            return f"Done — exported {count} task(s) to Google Calendar."
        return "Action completed successfully."

    def _normalize_action_payload(self, action_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        if action_name in ("create_tasks", "update_task") and normalized.get("deadline"):
            normalized["deadline"] = normalize_deadline(str(normalized["deadline"]))
        return normalized

    def _task_context_snippet(self, limit: int = 15) -> str:
        from ..actions.task_actions import list_tasks_action

        tasks = list_tasks_action()
        if not tasks:
            return "(no tasks)"
        lines = []
        for i, t in enumerate(tasks[:limit], start=1):
            dl = t.get("deadline") or "no deadline"
            lines.append(f"{i}. {t['title']} [{t.get('status')}] due {dl}")
        return "\n".join(lines)


_chat_agent: ChatAgent | None = None


def get_chat_agent() -> ChatAgent:
    global _chat_agent
    if _chat_agent is None:
        _chat_agent = ChatAgent()
    return _chat_agent
