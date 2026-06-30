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

The React dev server proxies `/api` to the Flask backend, so the browser stays
on one origin during Google login and session-based OAuth works without CORS
issues.

Open the app and click the chat button (bottom-left). For LLM-powered responses,
set `OPENAI_API_KEY` in a `.env` file (see `.env.example`). Without an API key,
the chatbot falls back to rule-based routing for common commands.

## Google Calendar export

TaskPilot can connect to Google Calendar once through the backend OAuth flow,
then export tasks later without asking the user to log in again. The frontend
does not need any Google OAuth variables.

Set the following backend environment variables in your `.env` file:

- `GOOGLE_OAUTH_CLIENT_ID` for the backend OAuth client.
- `GOOGLE_OAUTH_CLIENT_SECRET` for the backend OAuth client.
- `GOOGLE_CALENDAR_ID` for the target calendar, or leave it unset to use the
	default `primary` calendar.
- `GOOGLE_CALENDAR_TIMEZONE` for the event timezone, such as
	`America/New_York`, or leave it unset to use `UTC`.

Use `Connect Google Calendar` once, then `Export to Google Calendar` whenever
you want to sync tasks.

The backend derives the OAuth callback from the current origin, so the same-
origin dev setup works without any frontend Google OAuth env vars. Only set
`GOOGLE_OAUTH_REDIRECT_URI` if you are deploying behind a fixed callback URL.
