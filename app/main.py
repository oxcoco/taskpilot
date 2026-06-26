#!/usr/bin/env python3
"""TaskPilot CLI entry point.

Now the CLI uses the CoordinatorAgent to process user commands.
Supported commands (simple demo):
- add "<free text>"   → extract tasks, rank, schedule and print the schedule
- Any other text       → forward to the coordinator (future extensions)
"""

import sys
from typing import List

# Import the coordinator (will be created later)
from taskpilot.agents.coordinator_agent import CoordinatorAgent


def _print_schedule(schedule: dict) -> None:
    """Pretty‑print the schedule dict returned by SchedulerAgent."""
    if not schedule:
        print("[TaskPilot] No tasks scheduled.")
        return
    print("[TaskPilot] Generated schedule:")
    for date, titles in schedule.items():
        print(f"  {date}:")
        for t in titles:
            print(f"    - {t}")


def main() -> None:
    """Entry point for the TaskPilot command line interface.

    Usage examples:
        python -m taskpilot.app.main add "Finish OS project by Friday"
        python -m taskpilot.app.main "Plan my week"
    """
    if len(sys.argv) < 2:
        print("TaskPilot CLI – no arguments provided. Use '--help' for usage.")
        return

    # Simple parsing – first token is the command
    command = sys.argv[1].lower()
    args = sys.argv[2:]

    coordinator = CoordinatorAgent()

    if command == "add" and args:
        # Join the remaining args as free‑form text
        user_input = " ".join(args)
        # Coordinator will return a schedule dict
        schedule = coordinator.run(user_input)
        _print_schedule(schedule)
    else:
        # Fallback – just pass the raw input to the coordinator
        user_input = " ".join(sys.argv[1:])
        result = coordinator.run(user_input)
        print(result)


if __name__ == "__main__":
    main()
