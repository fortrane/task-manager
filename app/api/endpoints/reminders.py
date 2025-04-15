from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_active_user
from app.models import Reminder, Task, User
from app.schemas import (
    Reminder as ReminderSchema,
    ReminderCreate,
    ReminderUpdate,
)

router = APIRouter()


@router.post("/tasks/{task_id}", response_model=ReminderSchema)
async def create_reminder(
        task_id: int,
        reminder_in: ReminderCreate,
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

    reminder = Reminder(
        **reminder_in.dict(),
        task_id=task_id,
    )

    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    return reminder


@router.get("/tasks/{task_id}", response_model=List[ReminderSchema])
async def read_reminders(
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

    reminders = db.query(Reminder).filter(Reminder.task_id == task_id).all()
    return reminders


@router.get("/reminders/{reminder_id}", response_model=ReminderSchema)
async def read_reminder(
        reminder_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> Any:
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()

    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found",
        )

    # Check if reminder's task belongs to user
    task = db.query(Task).filter(
        Task.id == reminder.task_id, Task.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    return reminder


@router.put("/update/{reminder_id}", response_model=ReminderSchema)
async def update_reminder(
        reminder_id: int,
        reminder_in: ReminderUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> Any:
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()

    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found",
        )

    # Check if reminder's task belongs to user
    task = db.query(Task).filter(
        Task.id == reminder.task_id, Task.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    update_data = reminder_in.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(reminder, field, value)

    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    return reminder


@router.delete("/delete/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
        reminder_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> None:
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()

    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found",
        )

    # Check if reminder's task belongs to user
    task = db.query(Task).filter(
        Task.id == reminder.task_id, Task.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    db.delete(reminder)
    db.commit()

