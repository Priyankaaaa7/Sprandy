"""
services/llm_agent.py

The reasoning layer: turns a chat message into tool calls against
Sprandy's own database, then turns tool results into a reply.

Separation of concerns (matches the rest of the codebase):
- personality.py owns TONE.
- This file owns WHICH TOOLS EXIST and WHAT THEY'RE ALLOWED TO DO.
  The model can only ever call functions listed in TOOLS below — it
  cannot run arbitrary SQL or reach outside this whitelist.
- crud.py / services/postponement.py / services/summary_generator.py
  remain the single source of truth for data. This file never
  duplicates that logic, only calls into it.

Runs entirely against a local Ollama instance — no data leaves the
machine. If Ollama isn't running or the model isn't pulled, run_agent
raises an exception that the chat router turns into a clear 503.
"""
import json
from datetime import date

import ollama

from app import crud
from app.services import postponement, summary_generator, personality

# Change this if you pulled a different model (e.g. "qwen2.5:3b" for lower-resource machines).
OLLAMA_MODEL = "llama3.1"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_tasks",
            "description": "List the user's tasks. Use status='pending' for unfinished work.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed"],
                        "description": "Optional filter; omit to get everything.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_accountability",
            "description": (
                "Get tasks that have been postponed multiple times, with real evidence "
                "(dates, counts). ALWAYS call this before saying anything about "
                "procrastination, postponed tasks, or accountability."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_task",
            "description": "Create a new task for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "due_date": {"type": "string", "description": "YYYY-MM-DD, optional"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": "Mark a task as completed, given its numeric task_id.",
            "parameters": {
                "type": "object",
                "properties": {"task_id": {"type": "integer"}},
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "postpone_task",
            "description": (
                "Push a task's due date back. This logs evidence for the accountability "
                "system, so only call it when the user actually wants to postpone, not "
                "just discuss it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer"},
                    "new_due_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "reason": {"type": "string"},
                },
                "required": ["task_id", "new_due_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_journal_entry",
            "description": "Get the journal entry for a date (defaults to today if entry_date omitted).",
            "parameters": {
                "type": "object",
                "properties": {"entry_date": {"type": "string", "description": "YYYY-MM-DD, optional"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_summary",
            "description": "Get (or generate if missing) the summary for a date, defaults to today.",
            "parameters": {
                "type": "object",
                "properties": {"summary_date": {"type": "string", "description": "YYYY-MM-DD, optional"}},
            },
        },
    },
]


def _dispatch(conn, name: str, args: dict):
    """Executes exactly one tool call against real data. No tool here fabricates anything."""
    if name == "get_tasks":
        return crud.list_tasks(conn, args.get("status"))

    if name == "get_accountability":
        flags = postponement.get_accountability_flags(conn)
        return [{"task": f["task"]["title"], "message": f["message"]} for f in flags]

    if name == "add_task":
        return crud.create_task(conn, args["title"], None, args.get("priority", "medium"), args.get("due_date"))

    if name == "complete_task":
        task = crud.get_task(conn, args["task_id"])
        if not task:
            return {"error": f"No task with id {args['task_id']}"}
        return crud.complete_task(conn, args["task_id"])

    if name == "postpone_task":
        task = crud.get_task(conn, args["task_id"])
        if not task:
            return {"error": f"No task with id {args['task_id']}"}
        return crud.postpone_task(conn, args["task_id"], args["new_due_date"], args.get("reason"))

    if name == "get_journal_entry":
        d = args.get("entry_date") or str(date.today())
        entry = crud.get_journal_entry_by_date(conn, d)
        return entry or {"detail": f"No journal entry for {d}"}

    if name == "get_daily_summary":
        d = args.get("summary_date") or str(date.today())
        existing = crud.get_daily_summary(conn, d)
        return existing or summary_generator.generate_daily_summary(conn, d)

    return {"error": f"Unknown tool: {name}"}


def run_agent(conn, message: str, history: list | None = None, max_tool_rounds: int = 4):
    """
    Runs one user turn through the local model. Loops on tool calls
    (executing each against real data) until the model produces a
    final text reply, or max_tool_rounds is hit.

    Returns: (reply_text, updated_history_without_system_prompt, tool_trace)
    """
    messages = [{"role": "system", "content": personality.SYSTEM_PROMPT}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": message})

    tool_trace = []

    for _ in range(max_tool_rounds):
        response = ollama.chat(model=OLLAMA_MODEL, messages=messages, tools=TOOLS)
        msg = response["message"]
        tool_calls = msg.get("tool_calls")

        if not tool_calls:
            final_text = msg.get("content", "")
            messages.append({"role": "assistant", "content": final_text})
            return final_text, messages[1:], tool_trace

        messages.append(msg)
        for call in tool_calls:
            fn_name = call["function"]["name"]
            fn_args = call["function"].get("arguments", {})
            if isinstance(fn_args, str):
                fn_args = json.loads(fn_args)
            result = _dispatch(conn, fn_name, fn_args)
            tool_trace.append({"tool": fn_name, "args": fn_args, "result": result})
            messages.append({"role": "tool", "content": json.dumps(result, default=str)})

    return (
        "I went down a rabbit hole looking that up and didn't land anywhere useful — try rephrasing?",
        messages[1:],
        tool_trace,
    )