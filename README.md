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

# Or start the API + React frontend (includes chat assistant)
make frontend
```

## Chat assistant

TaskPilot includes a conversational chatbot that can list tasks, check deadlines,
generate schedules, and propose task changes. **All create, update, and delete
actions require explicit user approval** before they are executed.

```bash
# Start the API server
PYTHONPATH=. python -m taskpilot.app.api

# In another terminal, start the frontend
cd frontend && npm install && npm run dev
```

Open the app and click the chat button (bottom-left). For LLM-powered responses,
set `OPENAI_API_KEY` in a `.env` file (see `.env.example`). Without an API key,
the chatbot falls back to rule-based routing for common commands.
