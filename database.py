"""
database.py
Handles SQLite connection setup for Sprandy.
Designed so swapping to Postgres later only requires changing this file.

THREAD-SAFETY NOTE (read before touching this file):
FastAPI runs sync ('def', not 'async def') routes and sync generator
dependencies inside a worker thread pool. For a single request, the
code before `yield` in db_dependency() (creating the connection) and
the code after `yield` (commit/rollback/close) are NOT guaranteed to
execute on the same OS thread — FastAPI can hand teardown off to a
different pool thread than the one that did setup. sqlite3's default
check_same_thread=True enforces that every operation on a connection
happens on the exact thread that created it, so that thread-handoff
raises sqlite3.ProgrammingError, even with only one user active.

check_same_thread=False below is the correct fix for this codebase
specifically because every connection is still private to a single
request (created fresh in get_connection(), never reused or shared
across requests, never stored as a module-level/global connection).
We are not disabling protection against real concurrent multi-thread
use of one shared connection — there is no shared connection here.
If that ever changes (e.g. a background notification poller thread
sharing a connection with web requests), give that thread its own
connection via get_connection() rather than passing one connection
across threads.
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "sprandy.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    """
    Create a brand-new SQLite connection. Called fresh for every
    request (via db_dependency) and for one-off scripts (init_db).
    Never share the returned object across threads or requests.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False,  # see module docstring — justified, not a blanket unlock
        timeout=10,               # seconds to wait on a lock before raising "database is locked"
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL mode lets readers and a writer work concurrently instead of
    # blocking each other, which matters once notifications/background
    # jobs start touching the DB alongside web requests.
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def get_db():
    """Context manager for use in standalone scripts (not request-scoped)."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Run schema.sql against the database. Safe to call repeatedly."""
    conn = get_connection()
    try:
        with open(SCHEMA_PATH, "r") as f:
            conn.executescript(f.read())
        conn.commit()
    finally:
        conn.close()


def db_dependency():
    """
    FastAPI dependency: yields exactly ONE fresh connection per request.
    Nothing is pooled or shared between requests — each call to this
    generator creates its own connection and tears it down itself.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
