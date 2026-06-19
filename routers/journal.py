"""
routers/journal.py
Endpoints for daily journal/notes. One entry per day (upsert on same date).
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import date
from app.database import db_dependency
from app import crud
from app.models import JournalCreate, JournalUpdate

router = APIRouter(prefix="/journal", tags=["journal"])


@router.post("")
def create_or_update_entry(entry: JournalCreate, conn=Depends(db_dependency)):
    return crud.upsert_journal_entry(conn, entry.entry_date, entry.content, entry.mood)


@router.get("")
def list_entries(start_date: Optional[date] = None, end_date: Optional[date] = None,
                  conn=Depends(db_dependency)):
    return crud.list_journal_entries(conn, start_date, end_date)


@router.get("/{entry_date}")
def get_entry(entry_date: date, conn=Depends(db_dependency)):
    entry = crud.get_journal_entry_by_date(conn, entry_date)
    if not entry:
        raise HTTPException(status_code=404, detail="No journal entry for this date")
    return entry


@router.put("/{entry_date}")
def update_entry(entry_date: date, payload: JournalUpdate, conn=Depends(db_dependency)):
    existing = crud.get_journal_entry_by_date(conn, entry_date)
    if not existing:
        raise HTTPException(status_code=404, detail="No journal entry for this date")
    content = payload.content if payload.content is not None else existing["content"]
    mood = payload.mood if payload.mood is not None else existing["mood"]
    return crud.upsert_journal_entry(conn, entry_date, content, mood)


@router.delete("/{entry_id}")
def delete_entry(entry_id: int, conn=Depends(db_dependency)):
    crud.delete_journal_entry(conn, entry_id)
    return {"detail": "Journal entry deleted"}
