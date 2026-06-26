# TaskPilot

**TaskPilot** is an AI‑powered task and scheduling assistant built with a lightweight,
multi‑agent architecture. It demonstrates how separate agents can cooperate
to extract tasks, assign priorities, generate schedules, and re‑plan when progress
updates arrive.

## Features (initial release)

- Parse natural‑language descriptions into structured tasks
- Automatic priority assignment based on deadlines
- Simple 9‑to‑5 daily schedule generation
- SQLite persistence for tasks
- Extensible skill‑based wrappers
- Command‑line interface (`python -m taskpilot.app.main`)

## Quick start

```bash
# Clone the repository (replace <repo-url> with the actual URL)
git clone <repo-url>
cd taskpilot

# Install dependencies
pip install -r requirements.txt

# Initialise the SQLite database
python -c "import taskpilot.database.db as db; db.create_tables()"

# Run the placeholder CLI (add a task)
python -m taskpilot.app.main add "Finish OS project by Friday"

# Or start the interactive UI
python -m taskpilot.app.run_ui
```
