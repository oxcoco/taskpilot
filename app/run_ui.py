#!/usr/bin/env python3
"""Simple interactive UI for TaskPilot.

Provides a text‑based menu that calls the helper functions in
`taskpilot.app.ui`. It demonstrates adding, listing, editing, deleting and
 toggling task completion, as well as deleting all tasks and viewing the schedule.
"""

import sys
import pathlib
from typing import List, Dict, Any

# Ensure project root is on PYTHONPATH when running as a script
project_root = pathlib.Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

# Try absolute import first; fallback to relative import if needed
try:
    from taskpilot.app.ui import (
        list_all_tasks,
        add_task_interactive,
        edit_task,
        delete_task_by_id,
        mark_done,
        mark_undone,
        delete_all_tasks,
        show_schedule,
        check_deadlines,
        generate_weekly_plan,
    )
except Exception:
    from .ui import (
        list_all_tasks,
        add_task_interactive,
        edit_task,
        delete_task_by_id,
        mark_done,
        mark_undone,
        delete_all_tasks,
        show_schedule,
        check_deadlines,
        generate_weekly_plan,
    )


def _resolve_task_id(user_input: str, tasks: List[Dict[str, Any]]) -> str:
    """Resolve a task ID from user input.

    The user may provide either a numeric index (as shown by the task list)
    or the raw UUID string. If the input can be parsed as an integer and falls
    within the range of ``tasks``, the corresponding task's ``id`` is returned.
    Otherwise the original string is returned (assumed to be a UUID).
    """
    try:
        idx = int(user_input)
        if 1 <= idx <= len(tasks):
            return tasks[idx - 1]["id"]
    except ValueError:
        pass
    return user_input


def _print_tasks(tasks: List[Dict[str, Any]]) -> None:
    """Pretty‑print a list of task dictionaries for the UI.

    Displays a numbered list with key fields.
    """
    if not tasks:
        print("[TaskPilot] No tasks found.")
        return
    print("[TaskPilot] Current tasks:")
    for i, t in enumerate(tasks, start=1):
        status = t.get("status")
        print(f"  {i}. {t.get('title')} (ID: {t.get('id')}) [{status}]")
        if t.get("deadline"):
            print(f"       Deadline: {t.get('deadline')}")
        if t.get("estimated_hours"):
            print(f"       Est. hours: {t.get('estimated_hours')}")
        if t.get("priority"):
            print(f"       Priority: {t.get('priority')}")
        if t.get("description"):
            print(f"       Desc: {t.get('description')}")


def _menu() -> None:
    while True:
        print("\n=== TaskPilot UI ===")
        print("1) List tasks")
        print("2) Add task")
        print("3) Edit task")
        print("4) Delete task")
        print("5) Mark task as done")
        print("6) Mark task as not done")
        print("7) Delete all tasks")

        print("8) View schedule")
        print("9) Check deadlines")
        print("10) Generate weekly plan")
        print("11) Exit")
        choice = input("Select an option: ").strip()

        if choice == "1":
            tasks = list_all_tasks()
            _print_tasks(tasks)
        elif choice == "2":
            title = input("Title: ").strip()
            desc = input("Description (optional): ").strip()
            deadline = input("Deadline (e.g. 2023-12-31 or today/tomorrow): ").strip() or None
            priority = input("Priority [HIGH/MEDIUM/LOW] (default MEDIUM): ").strip() or "MEDIUM"
            est = input("Estimated hours (default 1.0): ").strip()
            est_val = float(est) if est else 1.0
            add_task_interactive(title, description=desc, deadline=deadline,
                                 priority=priority, estimated_hours=est_val)
            print("Task added.")
        elif choice == "3":
            tasks = list_all_tasks()
            task_input = input("Task ID or number to edit: ").strip()
            task_id = _resolve_task_id(task_input, tasks)
            print("Leave a field empty to keep current value.")
            updates: Dict[str, Any] = {}
            new_title = input("New title: ").strip()
            if new_title:
                updates["title"] = new_title
            new_desc = input("New description: ").strip()
            if new_desc:
                updates["description"] = new_desc
            new_deadline = input("New deadline: ").strip()
            if new_deadline:
                updates["deadline"] = new_deadline
            new_priority = input("New priority [HIGH/MEDIUM/LOW]: ").strip()
            if new_priority:
                updates["priority"] = new_priority
            new_est = input("New estimated hours: ").strip()
            if new_est:
                updates["estimated_hours"] = float(new_est)
            if updates:
                edit_task(task_id, **updates)
                print("Task updated.")
            else:
                print("No changes supplied.")
        elif choice == "4":
            tasks = list_all_tasks()
            task_input = input("Task ID or number to delete: ").strip()
            task_id = _resolve_task_id(task_input, tasks)
            delete_task_by_id(task_id)
            print("Task deleted.")
        elif choice == "5":
            tasks = list_all_tasks()
            task_input = input("Task ID or number to mark done: ").strip()
            task_id = _resolve_task_id(task_input, tasks)
            mark_done(task_id)
            print("Task marked as completed.")
        elif choice == "6":
            tasks = list_all_tasks()
            task_input = input("Task ID or number to mark not done: ").strip()
            task_id = _resolve_task_id(task_input, tasks)
            mark_undone(task_id)
            print("Task marked as pending.")
        elif choice == "7":
            confirm = input("Are you sure you want to delete ALL tasks? (yes/no): ").strip().lower()
            if confirm == "yes":
                delete_all_tasks()
                print("All tasks deleted.")
            else:
                print("Operation cancelled.")
        elif choice == "8":
            show_schedule()
        elif choice == "9":
            check_deadlines()
            print("Deadlines checked.")
        elif choice == "10":
            plan = generate_weekly_plan()
            print(plan)
        elif choice == "11":
            print("Good‑bye!")
            sys.exit(0)
        else:
            print("Invalid option, please try again.")


if __name__ == "__main__":
    _menu()
