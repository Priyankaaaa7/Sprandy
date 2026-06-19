"""
services/summary_generator.py
Rule-based summary generation for the MVP. No LLM dependency —
this keeps Sprandy fully offline from day one. The function
signatures here are intentionally LLM-ready: a future version can
replace the body of generate_daily_summary_text with an Ollama call
that receives the same `data` dict and returns text instead.
"""
from datetime import date, timedelta
from app import crud
from app.services import postponement


def generate_daily_summary_text(data: dict, summary_date) -> str:
    completed = data["completed"]
    pending = data["pending"]
    postponed = data["postponed"]

    lines = [f"Daily summary for {summary_date}:"]

    if completed:
        lines.append(f"- Completed {len(completed)} task(s): " +
                     ", ".join(t["title"] for t in completed))
    else:
        lines.append("- No tasks completed today.")

    if pending:
        lines.append(f"- Still pending ({len(pending)}): " +
                      ", ".join(t["title"] for t in pending))

    if postponed:
        lines.append(f"- Postponed today ({len(postponed)}): " +
                      ", ".join(t["title"] for t in postponed))

    if not completed and pending:
        lines.append("- Heads up: nothing got finished while tasks sat waiting. Tomorrow's a clean slate, use it.")
    elif completed and not pending and not postponed:
        lines.append("- Clean day. Everything that was due got done.")

    return "\n".join(lines)


def generate_daily_summary(conn, summary_date=None):
    summary_date = summary_date or date.today()
    data = crud.get_tasks_for_date(conn, summary_date)
    text = generate_daily_summary_text(data, summary_date)
    return crud.save_daily_summary(
        conn,
        summary_date,
        completed=len(data["completed"]),
        pending=len(data["pending"]),
        postponed=len(data["postponed"]),
        text=text,
    )


def generate_weekly_summary_text(daily_summaries, flags, week_start, week_end) -> str:
    total_completed = sum(s["tasks_completed"] for s in daily_summaries)
    total_pending = daily_summaries[-1]["tasks_pending"] if daily_summaries else 0
    total_postponed = sum(s["tasks_postponed"] for s in daily_summaries)

    lines = [f"Weekly summary {week_start} to {week_end}:"]
    lines.append(f"- Total tasks completed: {total_completed}")
    lines.append(f"- Total postponements logged: {total_postponed}")
    lines.append(f"- Tasks still pending at week end: {total_pending}")

    if flags:
        lines.append("- Accountability flags this week:")
        for f in flags:
            lines.append(f"  * {f['message']}")
    else:
        lines.append("- No chronic procrastination flags this week. Solid.")

    return "\n".join(lines)


def generate_weekly_summary(conn, week_start=None):
    """week_start defaults to the most recent Monday."""
    if week_start is None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    daily_summaries = []
    d = week_start
    while d <= week_end:
        s = crud.get_daily_summary(conn, d)
        if not s:
            s = generate_daily_summary(conn, d)
        daily_summaries.append(s)
        d += timedelta(days=1)

    flags = postponement.get_accountability_flags(conn)
    text = generate_weekly_summary_text(daily_summaries, flags, week_start, week_end)

    total_completed = sum(s["tasks_completed"] for s in daily_summaries)
    total_pending = daily_summaries[-1]["tasks_pending"] if daily_summaries else 0
    total_postponed = sum(s["tasks_postponed"] for s in daily_summaries)

    return crud.save_weekly_summary(
        conn, week_start, week_end, total_completed, total_pending, total_postponed, text
    )
