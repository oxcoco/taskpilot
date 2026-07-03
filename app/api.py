#!/usr/bin/env python3
"""Flask API backend for TaskPilot.

Provides endpoints for tasks (CRUD), generating schedules, checking deadlines,
and generating weekly plans.
"""

import os
import pathlib
import secrets
import sys
from urllib.parse import urlencode
from flask import Flask, jsonify, redirect, request, session
from flask_cors import CORS

# Add project root to PYTHONPATH
project_root = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from taskpilot.app.ui import (
    list_all_tasks,
    add_task_interactive,
    edit_task,
    delete_task_by_id,
    mark_done,
    mark_undone,
    delete_all_tasks,
    check_deadlines,
    generate_weekly_plan,
)
from taskpilot.agents.task_agent import TaskAgent
from taskpilot.agents.priority_agent import PriorityAgent
from taskpilot.agents.scheduler_agent import SchedulerAgent
from taskpilot.actions.schedule_actions import export_tasks_to_google_calendar_action
from taskpilot.database.google_oauth import (
    delete_google_oauth_credentials,
    google_oauth_connected,
    load_google_oauth_credentials,
    save_google_oauth_credentials,
)
from taskpilot.mcp.google_oauth import build_google_authorization_url, exchange_code_for_tokens

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "taskpilot-dev-secret")


def _cors_origins() -> list[str]:
    """Build the allowed CORS origins list.

    - `CORS_ALLOWED_ORIGINS`: comma-separated full origins for precise control.
    - Fallback includes local dev hosts and common hosted frontend domains.
    """
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://localhost:5173",
        "https://127.0.0.1:5173",
        r"https://.*\.github\.io",
        r"https://.*\.onrender\.com",
    ]


CORS(
    app,
    resources={r"/api/*": {"origins": _cors_origins()}},
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
)

@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    try:
        tasks = list_all_tasks()
        return jsonify(tasks), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/tasks", methods=["POST"])
def create_task():
    try:
        data = request.json or {}
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        deadline = data.get("deadline")
        priority = data.get("priority", "MEDIUM").strip()
        estimated_hours = float(data.get("estimated_hours", 1.0))

        if not title:
            return jsonify({"error": "Title is required"}), 400

        add_task_interactive(
            title=title,
            description=description,
            deadline=deadline,
            priority=priority,
            estimated_hours=estimated_hours,
        )
        return jsonify({"message": "Task added successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/tasks/<task_id>", methods=["PATCH"])
def update_task_endpoint(task_id):
    try:
        data = request.json or {}
        updates = {}
        if "title" in data:
            updates["title"] = data["title"]
        if "description" in data:
            updates["description"] = data["description"]
        if "deadline" in data:
            updates["deadline"] = data["deadline"]
        if "priority" in data:
            updates["priority"] = data["priority"]
        if "estimated_hours" in data:
            updates["estimated_hours"] = float(data["estimated_hours"])
        if "status" in data:
            updates["status"] = data["status"]

        if updates:
            edit_task(task_id, **updates)
            return jsonify({"message": "Task updated successfully"}), 200
        else:
            return jsonify({"message": "No updates provided"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task_endpoint(task_id):
    try:
        delete_task_by_id(task_id)
        return jsonify({"message": "Task deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/tasks/<task_id>/done", methods=["POST"])
def mark_task_done(task_id):
    try:
        mark_done(task_id)
        return jsonify({"message": "Task marked as completed"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/tasks/<task_id>/undone", methods=["POST"])
def mark_task_undone(task_id):
    try:
        mark_undone(task_id)
        return jsonify({"message": "Task marked as pending"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/tasks", methods=["DELETE"])
def delete_tasks_all():
    try:
        delete_all_tasks()
        return jsonify({"message": "All tasks deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/schedule", methods=["GET"])
def get_schedule():
    try:
        tasks = TaskAgent.list_tasks()
        pending_tasks = [t for t in tasks if t.status.value != "COMPLETED"]
        completed_tasks = [t for t in tasks if t.status.value == "COMPLETED"]
        
        pending_dicts = [t.to_dict() for t in pending_tasks]
        if pending_dicts:
            ranked = PriorityAgent().rank_tasks(pending_dicts)
            schedule = SchedulerAgent.generate_schedule(ranked) or {}
        else:
            schedule = {}
            
        if completed_tasks:
            schedule["Completed"] = [t.title for t in completed_tasks]
            
        return jsonify(schedule), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/check_deadlines", methods=["POST"])
def trigger_deadline_check():
    try:
        from taskpilot.skills.deadline_check import get_deadline_summary

        return jsonify(get_deadline_summary()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/weekly_plan", methods=["GET"])
def get_weekly_plan():
    try:
        plan = generate_weekly_plan()
        return jsonify({"plan": plan}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/google_calendar/export", methods=["POST"])
def export_google_calendar():
    try:
        data = request.json or {}
        result = export_tasks_to_google_calendar_action(
            task_ids=data.get("task_ids"),
            calendar_id=data.get("calendar_id"),
            timezone=data.get("timezone"),
            include_completed=bool(data.get("include_completed", True)),
            include_undated=bool(data.get("include_undated", True)),
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/google-calendar/connect", methods=["GET"])
def connect_google_calendar():
    try:
        client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
        redirect_uri = os.getenv(
            "GOOGLE_OAUTH_REDIRECT_URI",
            f"{request.url_root.rstrip('/')}/api/google-calendar/callback",
        )
        if not client_id:
            return jsonify({"error": "GOOGLE_OAUTH_CLIENT_ID is required"}), 500

        state = secrets.token_urlsafe(32)
        session["google_oauth_state"] = state
        session["google_oauth_return_to"] = request.args.get("return_to") or request.headers.get("Origin") or "/"

        authorization_url = build_google_authorization_url(
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
        )
        return redirect(authorization_url)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/google-calendar/callback", methods=["GET"])
def google_calendar_callback():
    try:
        stored_state = session.pop("google_oauth_state", None)
        return_to = session.pop("google_oauth_return_to", "/")
        redirect_uri = os.getenv(
            "GOOGLE_OAUTH_REDIRECT_URI",
            f"{request.url_root.rstrip('/')}/api/google-calendar/callback",
        )
        error_value = request.args.get("error")
        if error_value:
            query = urlencode({"google_calendar": "error", "message": error_value})
            return redirect(f"{return_to}{'&' if '?' in return_to else '?'}{query}")

        if request.args.get("state") != stored_state:
            query = urlencode({"google_calendar": "error", "message": "Invalid OAuth state"})
            return redirect(f"{return_to}{'&' if '?' in return_to else '?'}{query}")

        code = request.args.get("code")
        if not code:
            query = urlencode({"google_calendar": "error", "message": "Missing authorization code"})
            return redirect(f"{return_to}{'&' if '?' in return_to else '?'}{query}")

        client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
        if not client_id or not client_secret:
            return jsonify({"error": "GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET are required"}), 500

        token_data = exchange_code_for_tokens(
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
        refresh_token = token_data.get("refresh_token")
        if refresh_token:
            save_google_oauth_credentials(
                refresh_token=refresh_token,
                scope=token_data.get("scope"),
            )
        query = urlencode({"google_calendar": "connected"})
        return redirect(f"{return_to}{'&' if '?' in return_to else '?'}{query}")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/google-calendar/status", methods=["GET"])
def google_calendar_status():
    try:
        creds = load_google_oauth_credentials()
        return (
            jsonify(
                {
                    "connected": bool(creds),
                    "calendar_id": os.getenv("GOOGLE_CALENDAR_ID", "primary"),
                    "timezone": os.getenv("GOOGLE_CALENDAR_TIMEZONE", "UTC"),
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/google-calendar/disconnect", methods=["POST"])
def google_calendar_disconnect():
    try:
        delete_google_oauth_credentials()
        return jsonify({"connected": False}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat_message():
    try:
        from taskpilot.agents.chat_agent import get_chat_agent

        data = request.json or {}
        message = (data.get("message") or "").strip()
        session_id = data.get("session_id")
        if not message:
            return jsonify({"error": "message is required"}), 400

        agent = get_chat_agent()
        response = agent.handle_message(message, session_id)
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/approve", methods=["POST"])
def chat_approve():
    try:
        from taskpilot.agents.chat_agent import get_chat_agent

        data = request.json or {}
        session_id = data.get("session_id")
        pending_action_id = data.get("pending_action_id")
        if not session_id or not pending_action_id:
            return jsonify({"error": "session_id and pending_action_id are required"}), 400

        agent = get_chat_agent()
        response = agent.approve(session_id, pending_action_id)
        return jsonify(response), 200
    except KeyError as e:
        return jsonify({"error": str(e)}), 404
    except (PermissionError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/reject", methods=["POST"])
def chat_reject():
    try:
        from taskpilot.agents.chat_agent import get_chat_agent

        data = request.json or {}
        session_id = data.get("session_id")
        pending_action_id = data.get("pending_action_id")
        if not session_id or not pending_action_id:
            return jsonify({"error": "session_id and pending_action_id are required"}), 400

        agent = get_chat_agent()
        response = agent.reject(session_id, pending_action_id)
        return jsonify(response), 200
    except KeyError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/pending", methods=["GET"])
def chat_pending():
    try:
        from taskpilot.agents.chat_agent import get_chat_agent

        session_id = request.args.get("session_id")
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400

        agent = get_chat_agent()
        pending = agent.list_pending(session_id)
        return jsonify({"pending": pending}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/history", methods=["GET"])
def chat_history():
    try:
        from taskpilot.agents.chat_agent import get_chat_agent

        session_id = request.args.get("session_id")
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400

        agent = get_chat_agent()
        history = agent.get_history(session_id)
        return jsonify({"history": history}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
