#!/usr/bin/env python3
"""Flask API backend for TaskPilot.

Provides endpoints for tasks (CRUD), generating schedules, checking deadlines,
and generating weekly plans.
"""

import sys
import pathlib
import io
import contextlib
from flask import Flask, jsonify, request
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

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend running on other ports

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
