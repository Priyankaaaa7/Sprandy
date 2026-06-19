"""
routers/summaries.py
Endpoints to generate/fetch daily and weekly summaries.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import date
from app.database import db_dependency
from app import crud
from app.services import summary_generator

router = APIRouter(prefix="/summaries", tags=["summaries"])


@router.post("/daily/generate")
def generate_daily(summary_date: Optional[date] = None, conn=Depends(db_dependency)):
    return summary_generator.generate_daily_summary(conn, summary_date)


@router.get("/daily/{summary_date}")
def get_daily(summary_date: date, conn=Depends(db_dependency)):
    summary = crud.get_daily_summary(conn, summary_date)
    if not summary:
        raise HTTPException(status_code=404, detail="No summary for this date. Generate it first.")
    return summary


@router.post("/weekly/generate")
def generate_weekly(week_start: Optional[date] = None, conn=Depends(db_dependency)):
    return summary_generator.generate_weekly_summary(conn, week_start)


@router.get("/weekly")
def get_weekly(week_start: date, week_end: date, conn=Depends(db_dependency)):
    summary = crud.get_weekly_summary(conn, week_start, week_end)
    if not summary:
        raise HTTPException(status_code=404, detail="No summary for this week. Generate it first.")
    return summary
