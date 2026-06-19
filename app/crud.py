"""
crud.py
All direct database operations live here. Routers call these functions
instead of writing SQL inline, so storage logic stays in one place.
"""
import sqlite3
from datetime import date


# ---------- Tasks ----------

def create_task(conn: sqlite3.Connection, title, description, priority, due_date):
    cur = conn.execute(
        """INSERT INTO tasks (title, description, priority, due_date)
           VALUES (?, ?, ?, ?)""",
        (title, description, priority, str(due_date) if due_date else None),
    )
    return get_task(conn, cur.lastrowid)


def get_task(conn: sqlite3.Connection, task_id: int):
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return dict(row) if row else None


def list_tasks(conn: sqlite3.Connection, status: str = None):
    if status:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status = ? ORDER BY due_date IS NULL, due_date ASC, priority DESC",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY status = 'completed', due_date IS NULL, due_date ASC"
        ).fetchall()
    return [dict(r) for r in rows]


def update_task(conn: sqlite3.Connection, task_id: int, fields: dict):
    if not fields:
        return get_task(conn, task_id)
    fields = {k: (str(v) if isinstance(v, date) else v) for k, v in fields.items()}
    set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values()) + [task_id]
    conn.execute(
        f"UPDATE tasks SET {set_clause}, updated_at = datetime('now') WHERE id = ?",
        values,
    )
    return get_task(conn, task_id)


def delete_task(conn: sqlite3.Connection, task_id: int):
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


def complete_task(conn: sqlite3.Connection, task_id: int):
    conn.execute(
        """UPDATE tasks
           SET status = 'completed', completed_at = datetime('now'), updated_at = datetime('now')
           WHERE id = ?""",
        (task_id,),
    )
    return get_task(conn, task_id)


def postpone_task(conn: sqlite3.Connection, task_id: int, new_due_date, reason: str = None):
    task = get_task(conn, task_id)
    if not task:
        return None
    old_due_date = task["due_date"]
    conn.execute(
        """INSERT INTO task_postponements (task_id, old_due_date, new_due_date, reason)
           VALUES (?, ?, ?, ?)""",
        (task_id, old_due_date, str(new_due_date), reason),
    )
    conn.execute(
        """UPDATE tasks
           SET due_date = ?,
               postponed_count = postponed_count + 1,
               last_postponed_date = date('now'),
               updated_at = datetime('now')
           WHERE id = ?""",
        (str(new_due_date), task_id),
    )
    return get_task(conn, task_id)


def get_postponement_history(conn: sqlite3.Connection, task_id: int):
    rows = conn.execute(
        "SELECT * FROM task_postponements WHERE task_id = ? ORDER BY postponed_at ASC",
        (task_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_overdue_tasks(conn: sqlite3.Connection):
    rows = conn.execute(
        """SELECT * FROM tasks
           WHERE status != 'completed' AND due_date IS NOT NULL AND due_date < date('now')
           ORDER BY due_date ASC"""
    ).fetchall()
    return [dict(r) for r in rows]


def get_chronic_postponers(conn: sqlite3.Connection, threshold: int = 2):
    rows = conn.execute(
        """SELECT * FROM tasks
           WHERE status != 'completed' AND postponed_count >= ?
           ORDER BY postponed_count DESC""",
        (threshold,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------- Journal ----------

def upsert_journal_entry(conn: sqlite3.Connection, entry_date, content, mood):
    existing = conn.execute(
        "SELECT id FROM journal_entries WHERE entry_date = ?", (str(entry_date),)
    ).fetchone()
    if existing:
        conn.execute(
            """UPDATE journal_entries
               SET content = ?, mood = ?, updated_at = datetime('now')
               WHERE entry_date = ?""",
            (content, mood, str(entry_date)),
        )
        entry_id = existing["id"]
    else:
        cur = conn.execute(
            """INSERT INTO journal_entries (entry_date, content, mood)
               VALUES (?, ?, ?)""",
            (str(entry_date), content, mood),
        )
        entry_id = cur.lastrowid
    return get_journal_entry_by_id(conn, entry_id)


def get_journal_entry_by_id(conn: sqlite3.Connection, entry_id: int):
    row = conn.execute("SELECT * FROM journal_entries WHERE id = ?", (entry_id,)).fetchone()
    return dict(row) if row else None


def get_journal_entry_by_date(conn: sqlite3.Connection, entry_date):
    row = conn.execute(
        "SELECT * FROM journal_entries WHERE entry_date = ?", (str(entry_date),)
    ).fetchone()
    return dict(row) if row else None


def list_journal_entries(conn: sqlite3.Connection, start_date=None, end_date=None):
    if start_date and end_date:
        rows = conn.execute(
            """SELECT * FROM journal_entries
               WHERE entry_date BETWEEN ? AND ?
               ORDER BY entry_date DESC""",
            (str(start_date), str(end_date)),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM journal_entries ORDER BY entry_date DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def delete_journal_entry(conn: sqlite3.Connection, entry_id: int):
    conn.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))


# ---------- Summaries (storage only — generation logic lives in services) ----------

def save_daily_summary(conn: sqlite3.Connection, summary_date, completed, pending, postponed, text):
    conn.execute(
        """INSERT INTO daily_summaries (summary_date, tasks_completed, tasks_pending, tasks_postponed, summary_text)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(summary_date) DO UPDATE SET
               tasks_completed = excluded.tasks_completed,
               tasks_pending = excluded.tasks_pending,
               tasks_postponed = excluded.tasks_postponed,
               summary_text = excluded.summary_text""",
        (str(summary_date), completed, pending, postponed, text),
    )
    row = conn.execute(
        "SELECT * FROM daily_summaries WHERE summary_date = ?", (str(summary_date),)
    ).fetchone()
    return dict(row)


def get_daily_summary(conn: sqlite3.Connection, summary_date):
    row = conn.execute(
        "SELECT * FROM daily_summaries WHERE summary_date = ?", (str(summary_date),)
    ).fetchone()
    return dict(row) if row else None


def save_weekly_summary(conn: sqlite3.Connection, week_start, week_end, completed, pending, postponed, text):
    conn.execute(
        """INSERT INTO weekly_summaries (week_start, week_end, tasks_completed, tasks_pending, tasks_postponed, summary_text)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(week_start, week_end) DO UPDATE SET
               tasks_completed = excluded.tasks_completed,
               tasks_pending = excluded.tasks_pending,
               tasks_postponed = excluded.tasks_postponed,
               summary_text = excluded.summary_text""",
        (str(week_start), str(week_end), completed, pending, postponed, text),
    )
    row = conn.execute(
        "SELECT * FROM weekly_summaries WHERE week_start = ? AND week_end = ?",
        (str(week_start), str(week_end)),
    ).fetchone()
    return dict(row)


def get_weekly_summary(conn: sqlite3.Connection, week_start, week_end):
    row = conn.execute(
        "SELECT * FROM weekly_summaries WHERE week_start = ? AND week_end = ?",
        (str(week_start), str(week_end)),
    ).fetchone()
    return dict(row) if row else None


def get_tasks_for_date(conn: sqlite3.Connection, target_date):
    """Tasks completed on a given date, plus tasks still pending with that due date."""
    completed = conn.execute(
        "SELECT * FROM tasks WHERE date(completed_at) = ?", (str(target_date),)
    ).fetchall()
    pending = conn.execute(
        "SELECT * FROM tasks WHERE status != 'completed' AND due_date = ?", (str(target_date),)
    ).fetchall()
    postponed = conn.execute(
        "SELECT * FROM tasks WHERE last_postponed_date = ?", (str(target_date),)
    ).fetchall()
    return {
        "completed": [dict(r) for r in completed],
        "pending": [dict(r) for r in pending],
        "postponed": [dict(r) for r in postponed],
    }
