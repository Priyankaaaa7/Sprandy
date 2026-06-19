# Sprandy

A local-first AI productivity assistant built with FastAPI, SQLite, JavaScript, and Ollama.

Sprandy combines task management, journaling, accountability tracking, daily summaries, and a local AI agent into a single personal productivity system. Unlike traditional task managers, Sprandy's AI can interact with real application data through tool-calling, allowing it to retrieve tasks, identify procrastination patterns, create new tasks, and provide evidence-based accountability.

## Current Features

### Productivity System

* Task creation, editing, completion, and deletion
* Due dates and priority levels
* Postponement tracking with full history
* Accountability detection for chronically postponed tasks

### Journaling

* Daily journal entries
* Mood tracking
* Historical journal retrieval

### Summaries

* Daily productivity summaries
* Weekly productivity summaries
* Generated from actual task and journal data

### Local AI Agent

* Runs entirely through Ollama
* Supports tool-calling
* Reads real task data instead of guessing
* Can retrieve tasks
* Can create tasks
* Can postpone tasks
* Can access accountability information
* Works completely offline

## Architecture

Sprandy follows a layered architecture:

Frontend (HTML/CSS/JS)
↓
FastAPI API Layer
↓
Agent / Tool Layer
↓
Business Logic (Services)
↓
SQLite Database

The AI model never accesses the database directly. All actions are performed through a controlled tool interface, ensuring responses are grounded in real application data.

## Privacy First

All core functionality runs locally:

* SQLite database stored on-device
* Journal entries never leave the machine
* Tasks remain local
* Ollama model runs locally
* No external API required

This makes Sprandy suitable for personal productivity tracking without relying on cloud services.

# Sprandy MVP (v0.2.0)

A local-first personal productivity assistant. Single user, SQLite storage,
FastAPI backend, plain HTML/CSS/JS frontend. No internet connection required.

## Changelog

- **v0.11** — Dashboard rebuilt around four explicit sections: Today's Tasks,
  Accountability, Journal, Summary. Today's task list filters to due-today/
  overdue/no-date items; full task list is collapsed behind a `<details>`
  toggle so the dashboard stays scannable. Summary card auto-loads
  yesterday's summary on page load instead of requiring a click.
- **v0.12** — Added `GET /accountability`, a simplified, dashboard-facing
  version of the existing postponement-detection service:
  `{"flags": [{"task": "...", "message": "..."}]}`. This is the endpoint
  a future personality/LLM layer should read its evidence from.

## Setup

```bash
cd sprandy
pip install -r requirements.txt
python run.py
```

Then open **http://127.0.0.1:8000** in your browser. The database file is
created automatically at `data/sprandy.db` on first run — no manual setup.

## Folder Structure

```
sprandy/
├── app/
│   ├── main.py                  # FastAPI app, mounts routers + static UI
│   ├── database.py              # SQLite connection + schema init
│   ├── models.py                # Pydantic request/response schemas
│   ├── crud.py                  # All raw DB read/write logic
│   ├── schema.sql                # Table definitions
│   ├── routers/
│   │   ├── tasks.py             # /tasks endpoints
│   │   ├── journal.py           # /journal endpoints
│   │   ├── summaries.py         # /summaries endpoints
│   │   └── notifications.py     # /notifications endpoints
│   ├── services/
│   │   ├── postponement.py      # Chronic-postponement detection + accountability messages
│   │   └── summary_generator.py # Daily/weekly summary text generation
│   └── static/
│       ├── index.html
│       ├── style.css
│       └── app.js
├── data/
│   └── sprandy.db                # Created automatically, not in version control
├── requirements.txt
├── run.py
└── README.md
```

## Database Schema

- **tasks** — title, description, status, priority, due_date, postponed_count,
  last_postponed_date, timestamps.
- **task_postponements** — one row per postponement event (old date → new date,
  optional reason). This is the "evidence" the accountability system uses.
- **journal_entries** — one row per calendar day (unique on `entry_date`).
- **daily_summaries** — one row per day, generated on demand.
- **weekly_summaries** — one row per week range, generated on demand.

## API Endpoints

**Tasks**

- `POST /tasks` — create
- `GET /tasks?status=pending` — list (optional status filter)
- `GET /tasks/{id}` — get one
- `PUT /tasks/{id}` — update fields
- `DELETE /tasks/{id}` — delete
- `POST /tasks/{id}/complete` — mark complete
- `POST /tasks/{id}/postpone` — push due date, logs evidence
- `GET /tasks/{id}/history` — postponement history for one task

**Journal**

- `POST /journal` — create or update today's (or any date's) entry
- `GET /journal?start_date=&end_date=` — list entries, optional range
- `GET /journal/{entry_date}` — get entry for a specific date
- `PUT /journal/{entry_date}` — partial update
- `DELETE /journal/{entry_id}` — delete

**Summaries**

- `POST /summaries/daily/generate?summary_date=` — generate/refresh a day's summary
- `GET /summaries/daily/{summary_date}` — fetch a stored summary
- `POST /summaries/weekly/generate?week_start=` — generate/refresh a week's summary
- `GET /summaries/weekly?week_start=&week_end=` — fetch a stored summary

**Notifications**

- `GET /notifications/unfinished` — overdue, incomplete tasks
- `GET /notifications/postponed?threshold=2` — chronically postponed tasks with evidence
- `GET /notifications/summary` — combined feed for a single notification view

Interactive API docs are auto-generated by FastAPI at **http://127.0.0.1:8000/docs**.

## How accountability detection works

Every time a task's due date is pushed back via `/tasks/{id}/postpone`, a row
is written to `task_postponements` with the old date, new date, and reason.
`services/postponement.py` reads that history back and:

1. Flags any task with `postponed_count >= threshold` (default 2).
2. Builds a plain-text message citing the actual date history as evidence —
   not just "you're procrastinating," but "here's the receipt."
3. Tone escalates with count (2 vs 3 vs 4+ postponements get different framing).

This is rule-based on purpose — no AI model is required for the MVP. The
function `build_callout_message()` is the single seam where a future local
LLM (e.g. via Ollama) can generate sharper, more personalized callouts using
the same evidence data, without touching the detection logic.

## Implementation plan (how this was built, step by step)

1. **Schema first** — defined `tasks`, `task_postponements`, `journal_entries`,
   `daily_summaries`, `weekly_summaries` before writing any code.
2. **Storage layer** (`database.py`, `crud.py`) — all SQL lives here, isolated
   from API and business logic, so the API contract won't change if SQLite is
   later swapped for Postgres.
3. **Business logic** (`services/`) — postponement detection and summary
   generation as pure functions operating on data dicts, independent of
   FastAPI, so they're testable and replaceable.
4. **API layer** (`routers/`) — thin FastAPI routers that validate input via
   Pydantic and delegate to `crud`/`services`.
5. **UI** — a single static HTML page with vanilla JS calling the API. No
   build step, no framework, so a beginner can read every line.
6. **Manual end-to-end test** — created tasks, postponed one three times,
   completed another, generated a journal entry, and generated both summary
   types, confirming the accountability flag appears with real evidence.


# Sprandy

A local-first productivity assistant built with FastAPI, SQLite, and Ollama. Features task management, journaling, accountability tracking, daily summaries, and an extensible AI coaching layer.
