from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_active_user
from app.models import Task, RecurringTask, User
from app.schemas import (
    Task as TaskSchema,
    TaskCreate,
    TaskUpdate,
    RecurringTask as RecurringTaskSchema,
    RecurringTaskCreate,
    RecurringTaskUpdate,
)
from app.utils.metrics import record_task_created, record_task_completed

router = APIRouter()


@router.post("/", response_model=TaskSchema)
async def create_task(
        task_in: TaskCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> Any:
    task = Task(
        **task_in.dict(),
        owner_id=current_user.id,
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    # Record metrics
    record_task_created(
        category=task.category.value,
        priority=task.priority.value,
    )

    return task


@router.get("/", response_model=List[TaskSchema])
async def read_tasks(
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> Any:
    query = db.query(Task).filter(Task.owner_id == current_user.id)

    # Apply filters if provided
    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)
    if category:
        query = query.filter(Task.category == category)

    tasks = query.offset(skip).limit(limit).all()
    return tasks


@router.get("/{task_id}", response_model=TaskSchema)
async def read_task(
        task_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> Any:
    task = db.query(Task).filter(
        Task.id == task_id, Task.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return task


@router.put("/{task_id}", response_model=TaskSchema)
async def update_task(
        task_id: int,
        task_in: TaskUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> Any:
    task = db.query(Task).filter(
        Task.id == task_id, Task.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    update_data = task_in.dict(exclude_unset=True)

    # If task status is being updated to "done", set completed_at
    if "status" in update_data and update_data["status"] == "done" and task.status != "done":
        update_data["completed_at"] = datetime.utcnow()

        # Record task completion metrics
        if task.completed_at is None:  # Only if it's being completed for the first time
            duration = (datetime.utcnow() - task.created_at).total_seconds()
            record_task_completed(
                category=task.category.value,
                priority=task.priority.value,
                duration_seconds=duration,
            )

    for field, value in update_data.items():
        setattr(task, field, value)

    db.add(task)
    db.commit()
    db.refresh(task)

    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
        task_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> None:
    task = db.query(Task).filter(
        Task.id == task_id, Task.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    db.delete(task)
    db.commit()


# Recurring Tasks Endpoints
@router.post("/{task_id}/recurring", response_model=RecurringTaskSchema)
async def create_recurring_task(
        task_id: int,
        recurring_task_in: RecurringTaskCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> Any:
    # Check if task exists and belongs to user
    task = db.query(Task).filter(
        Task.id == task_id, Task.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Check if recurring task already exists
    existing_recurring = db.query(RecurringTask).filter(
        RecurringTask.task_id == task_id
    ).first()

    if existing_recurring:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recurring task already exists for this task",
        )

    recurring_task = RecurringTask(
        **recurring_task_in.dict(),
        task_id=task_id,
    )

    db.add(recurring_task)
    db.commit()
    db.refresh(recurring_task)

    return recurring_task


@router.get("/{task_id}/recurring", response_model=RecurringTaskSchema)
async def read_recurring_task(
        task_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> Any:
    # Check if task exists and belongs to user
    task = db.query(Task).filter(
        Task.id == task_id, Task.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    recurring_task = db.query(RecurringTask).filter(
        RecurringTask.task_id == task_id
    ).first()

    if not recurring_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring task not found",
        )

    return recurring_task


@router.put("/{task_id}/recurring", response_model=RecurringTaskSchema)
async def update_recurring_task(
        task_id: int,
        recurring_task_in: RecurringTaskUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> Any:
    # Check if task exists and belongs to user
    task = db.query(Task).filter(
        Task.id == task_id, Task.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    recurring_task = db.query(RecurringTask).filter(
        RecurringTask.task_id == task_id
    ).first()

    if not recurring_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring task not found",
        )

    update_data = recurring_task_in.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(recurring_task, field, value)

    db.add(recurring_task)
    db.commit()
    db.refresh(recurring_task)

    return recurring_task


@router.delete("/{task_id}/recurring", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring_task(
        task_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> None:
    # Check if task exists and belongs to user
    task = db.query(Task).filter(
        Task.id == task_id, Task.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    recurring_task = db.query(RecurringTask).filter(
        RecurringTask.task_id == task_id
    ).first()

    if not recurring_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring task not found",
        )

    db.delete(recurring_task)
    db.commit()
