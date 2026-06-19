"""
models.py
Pydantic schemas used for request validation and response shaping.
Keeping these separate from the DB layer means the API contract
doesn't change even if storage moves to Postgres later.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date as date_type


# ---------- Tasks ----------

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: Optional[date_type] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[Literal["low", "medium", "high"]] = None
    status: Optional[Literal["pending", "in_progress", "completed"]] = None
    due_date: Optional[date_type] = None


class TaskPostpone(BaseModel):
    new_due_date: date_type
    reason: Optional[str] = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: str
    priority: str
    due_date: Optional[str]
    postponed_count: int
    last_postponed_date: Optional[str]
    created_at: str
    updated_at: str
    completed_at: Optional[str]


# ---------- Journal ----------

class JournalCreate(BaseModel):
    entry_date: date_type
    content: str = Field(..., min_length=1)
    mood: Optional[str] = None


class JournalUpdate(BaseModel):
    content: Optional[str] = None
    mood: Optional[str] = None


class JournalOut(BaseModel):
    id: int
    entry_date: str
    content: str
    mood: Optional[str]
    created_at: str
    updated_at: str


# ---------- Summaries ----------

class DailySummaryOut(BaseModel):
    id: int
    summary_date: str
    tasks_completed: int
    tasks_pending: int
    tasks_postponed: int
    summary_text: str
    created_at: str


class WeeklySummaryOut(BaseModel):
    id: int
    week_start: str
    week_end: str
    tasks_completed: int
    tasks_pending: int
    tasks_postponed: int
    summary_text: str
    created_at: str
