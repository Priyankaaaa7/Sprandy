"""
routers/notifications.py
Pull-based notifications for the MVP: the web UI / a future desktop
notifier polls these endpoints. No push infrastructure needed yet.
"""
from fastapi import APIRouter, Depends, Query
from app.database import db_dependency
from app import crud
from app.services import postponement

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/unfinished")
def unfinished_tasks(conn=Depends(db_dependency)):
    """Tasks that are overdue and not completed."""
    return postponement.get_overdue_flags(conn)


@router.get("/postponed")
def postponed_flags(threshold: int = Query(2, ge=1), conn=Depends(db_dependency)):
    """Tasks postponed >= threshold times, with evidence for accountability."""
    return postponement.get_accountability_flags(conn, threshold=threshold)


@router.get("/summary")
def notification_summary(conn=Depends(db_dependency)):
    """Combined feed: overdue + chronic postponers, for a single bell-icon view."""
    overdue = postponement.get_overdue_flags(conn)
    chronic = postponement.get_accountability_flags(conn)
    return {
        "overdue_count": len(overdue),
        "chronic_postpone_count": len(chronic),
        "overdue": overdue,
        "chronic": chronic,
    }


@router.get("/accountability")
def accountability(threshold: int = Query(2, ge=1), conn=Depends(db_dependency)):
    """
    Simplified, dashboard-friendly accountability feed.
    Returns just task name + callout message — the receipts, no clutter.
    This is the endpoint the personality layer will read from later.
    """
    flags = postponement.get_accountability_flags(conn, threshold=threshold)
    return {
        "flags": [
            {"task": f["task"]["title"], "task_id": f["task"]["id"], "message": f["message"]}
            for f in flags
        ]
    }
