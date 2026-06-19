-- Sprandy MVP schema
-- Single-user, local-first. SQLite now, Postgres-compatible SQL later.

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'pending',      -- pending | in_progress | completed
    priority TEXT NOT NULL DEFAULT 'medium',     -- low | medium | high
    due_date TEXT,                                -- ISO date 'YYYY-MM-DD'
    postponed_count INTEGER NOT NULL DEFAULT 0,
    last_postponed_date TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS task_postponements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    old_due_date TEXT,
    new_due_date TEXT,
    reason TEXT,
    postponed_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date TEXT NOT NULL UNIQUE,              -- one entry per day
    content TEXT NOT NULL,
    mood TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS daily_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary_date TEXT NOT NULL UNIQUE,
    tasks_completed INTEGER NOT NULL DEFAULT 0,
    tasks_pending INTEGER NOT NULL DEFAULT 0,
    tasks_postponed INTEGER NOT NULL DEFAULT 0,
    summary_text TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS weekly_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start TEXT NOT NULL,
    week_end TEXT NOT NULL,
    tasks_completed INTEGER NOT NULL DEFAULT 0,
    tasks_pending INTEGER NOT NULL DEFAULT 0,
    tasks_postponed INTEGER NOT NULL DEFAULT 0,
    summary_text TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(week_start, week_end)
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_journal_date ON journal_entries(entry_date);
