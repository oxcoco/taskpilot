import os, sys, datetime

# Ensure the project root is on PYTHONPATH based on script location
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
sys.path.append(project_root)

from taskpilot.app.ui import add_task_interactive, list_all_tasks, delete_all_tasks


def test_deadline_conversion():
    # Clean slate
    delete_all_tasks()
    # Add tasks with natural language deadlines
    add_task_interactive("Task Today", deadline="today")
    add_task_interactive("Task Tomorrow", deadline="tomorrow")
    # Retrieve tasks
    tasks = list_all_tasks()
    today_iso = datetime.date.today().isoformat()
    tomorrow_iso = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    # Verify deadlines are stored as ISO strings
    for task in tasks:
        if task["title"] == "Task Today":
            assert (
                task["deadline"] == today_iso
            ), f"Expected {today_iso}, got {task['deadline']}"
        if task["title"] == "Task Tomorrow":
            assert (
                task["deadline"] == tomorrow_iso
            ), f"Expected {tomorrow_iso}, got {task['deadline']}"
    print("All deadline conversion tests passed.")


if __name__ == "__main__":
    test_deadline_conversion()
