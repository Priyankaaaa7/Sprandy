"""
main.py
Sprandy MVP — FastAPI app entrypoint.
Run with: python run.py  (from project root)
"""
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.database import init_db, db_dependency
from app.routers import tasks, journal, summaries, notifications
from app.services import postponement

app = FastAPI(title="Sprandy", description="Local-first personal productivity assistant", version="0.12.0")

# Initialize DB schema on startup
init_db()

# API routers
app.include_router(tasks.router)
app.include_router(journal.router)
app.include_router(summaries.router)
app.include_router(notifications.router)


@app.get("/accountability", tags=["accountability"])
def accountability(threshold: int = 2, conn=Depends(db_dependency)):
    """
    v0.12 — top-level accountability feed.
    {"flags": [{"task": "...", "message": "..."}]}
    This is the seam where the personality layer reads its evidence from.
    """
    flags = postponement.get_accountability_flags(conn, threshold=threshold)
    return {
        "flags": [
            {"task": f["task"]["title"], "task_id": f["task"]["id"], "message": f["message"]}
            for f in flags
        ]
    }

# Static web UI
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_ui():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "Sprandy MVP"}
