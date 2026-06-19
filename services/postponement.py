"""
services/postponement.py
The "accountability" core of Sprandy. Rule-based for the MVP — no LLM
required. This module is the seam where an LLM-driven confrontational
personality can be plugged in later (see roadmap V2+).
"""
from app import crud


def get_accountability_flags(conn, threshold: int = 2):
    """
    Returns tasks that have been postponed enough times to warrant
    being called out, along with evidence (the postponement history).
    """
    chronic = crud.get_chronic_postponers(conn, threshold=threshold)
    flags = []
    for task in chronic:
        history = crud.get_postponement_history(conn, task["id"])
        flags.append({
            "task": task,
            "postponed_count": task["postponed_count"],
            "history": history,
            "message": build_callout_message(task, history),
        })
    return flags


def build_callout_message(task, history):
    """
    Plain-text accountability message with evidence. This is the
    'personality' seam — swap this function for an LLM call later
    without touching the detection logic above.
    """
    count = task["postponed_count"]
    title = task["title"]
    if count >= 4:
        tone = (
            f"'{title}' has been pushed back {count} times now. "
            f"At this point it's not on your calendar, it's a recurring guest star."
        )
    elif count == 3:
        tone = f"Third time postponing '{title}'. That's officially a pattern, not bad luck."
    else:
        tone = f"'{title}' has been postponed {count} times. Worth asking why."

    dates = [f"{h['old_due_date'] or '?'} -> {h['new_due_date']}" for h in history]
    evidence = "Postponement history: " + "; ".join(dates) if dates else ""
    return f"{tone} {evidence}".strip()


def get_overdue_flags(conn):
    """Tasks past their due date and not completed."""
    overdue = crud.get_overdue_tasks(conn)
    return [
        {
            "task": t,
            "message": f"'{t['title']}' was due {t['due_date']} and is still not done.",
        }
        for t in overdue
    ]
