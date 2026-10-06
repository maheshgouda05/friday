from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.task import Task


router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)

TaskTitle = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=200,
    ),
]


# ---------------------------------------------------------
# REQUEST MODELS
# ---------------------------------------------------------

class TaskCreate(BaseModel):
    title: TaskTitle

    description: str | None = Field(
        default=None,
        max_length=1000
    )


class TaskUpdate(BaseModel):
    title: TaskTitle | None = None

    description: str | None = Field(
        default=None,
        max_length=1000
    )

    completed: bool | None = None


# ---------------------------------------------------------
# CREATE TASK
# ---------------------------------------------------------

@router.post("/")
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db)
):
    task = Task(
        title=task_data.title,
        description=task_data.description,
        completed=False
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return task


# ---------------------------------------------------------
# GET ALL TASKS
# ---------------------------------------------------------

@router.get("/")
def get_tasks(
    db: Session = Depends(get_db)
):
    tasks = (
        db.query(Task)
        .order_by(Task.id.desc())
        .all()
    )

    return tasks


# ---------------------------------------------------------
# GET ONE TASK
# ---------------------------------------------------------

@router.get("/{task_id}")
def get_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .first()
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return task


# ---------------------------------------------------------
# UPDATE TASK
# ---------------------------------------------------------

@router.put("/{task_id}")
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db)
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .first()
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    if task_data.title is not None:
        task.title = task_data.title

    if task_data.description is not None:
        task.description = task_data.description

    if task_data.completed is not None:
        task.completed = task_data.completed

    db.commit()
    db.refresh(task)

    return task


# ---------------------------------------------------------
# COMPLETE TASK
# ---------------------------------------------------------

@router.patch("/{task_id}/complete")
def complete_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .first()
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    task.completed = True

    db.commit()
    db.refresh(task)

    return task


# ---------------------------------------------------------
# DELETE TASK
# ---------------------------------------------------------

@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .first()
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    db.delete(task)
    db.commit()

    return {
        "message": "Task deleted successfully",
        "task_id": task_id
    }