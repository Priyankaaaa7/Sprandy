"""
routers/tasks.py
Endpoints: create, list, update, delete, complete, postpone.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Literal
from app.database import db_dependency
from app import crud
from app.models import TaskCreate, TaskUpdate, TaskPostpone

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("")
def create_task(task: TaskCreate, conn=Depends(db_dependency)):
    return crud.create_task(conn, task.title, task.description, task.priority, task.due_date)


@router.get("")
def list_tasks(status: Optional[Literal["pending", "in_progress", "completed"]] = None,
               conn=Depends(db_dependency)):
    return crud.list_tasks(conn, status)


@router.get("/{task_id}")
def get_task(task_id: int, conn=Depends(db_dependency)):
    task = crud.get_task(conn, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}")
def update_task(task_id: int, task: TaskUpdate, conn=Depends(db_dependency)):
    existing = crud.get_task(conn, task_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")
    fields = {k: v for k, v in task.model_dump().items() if v is not None}
    return crud.update_task(conn, task_id, fields)


@router.delete("/{task_id}")
def delete_task(task_id: int, conn=Depends(db_dependency)):
    existing = crud.get_task(conn, task_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")
    crud.delete_task(conn, task_id)
    return {"detail": "Task deleted"}


@router.post("/{task_id}/complete")
def complete_task(task_id: int, conn=Depends(db_dependency)):
    existing = crud.get_task(conn, task_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")
    return crud.complete_task(conn, task_id)


@router.post("/{task_id}/postpone")
def postpone_task(task_id: int, payload: TaskPostpone, conn=Depends(db_dependency)):
    existing = crud.get_task(conn, task_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")
    return crud.postpone_task(conn, task_id, payload.new_due_date, payload.reason)


@router.get("/{task_id}/history")
def task_history(task_id: int, conn=Depends(db_dependency)):
    existing = crud.get_task(conn, task_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")
    return crud.get_postponement_history(conn, task_id)
