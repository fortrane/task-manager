from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_active_user
from app.models import Task, TimeTrack, User
from app.schemas import (
    TimeTrack as TimeTrackSchema,
    TimeTrackCreate,
    TimeTrackUpdate,
)

router = APIRouter()


@router.post("/tasks/{task_id}/time", response_model=TimeTrackSchema)
async def create_time_track(
        task_id: int,
        time_track_in: TimeTrackCreate,
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

    # Calculate duration if end_time is provided
    time_track_data = time_track_in.dict()
    if time_track_data.get("end_time") and time_track_data.get("start_time"):
        start_time = time_track_data["start_time"]
        end_time = time_track_data["end_time"]
        duration = int((end_time - start_time).total_seconds())
        time_track_data["duration"] = duration

    time_track = TimeTrack(
        **time_track_data,
        task_id=task_id,
    )

    db.add(time_track)
    db.commit()
    db.refresh(time_track)

    return time_track


@router.get("/tasks/{task_id}/time", response_model=List[TimeTrackSchema])
async def read_time_tracks(
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

    time_tracks = db.query(TimeTrack).filter(TimeTrack.task_id == task_id).all()
    return time_tracks


@router.get("/time/{time_track_id}", response_model=TimeTrackSchema)
async def read_time_track(
        time_track_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> Any:
    time_track = db.query(TimeTrack).filter(TimeTrack.id == time_track_id).first()

    if not time_track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time track not found",
        )

    # Check if time track's task belongs to user
    task = db.query(Task).filter(
        Task.id == time_track.task_id, Task.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    return time_track


@router.put("/time/{time_track_id}", response_model=TimeTrackSchema)
async def update_time_track(
        time_track_id: int,
        time_track_in: TimeTrackUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> Any:
    time_track = db.query(TimeTrack).filter(TimeTrack.id == time_track_id).first()

    if not time_track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time track not found",
        )

    # Check if time track's task belongs to user
    task = db.query(Task).filter(
        Task.id == time_track.task_id, Task.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    update_data = time_track_in.dict(exclude_unset=True)

    # If end_time is being updated, recalculate duration
    if "end_time" in update_data:
        end_time = update_data["end_time"]
        if end_time:
            duration = int((end_time - time_track.start_time).total_seconds())
            update_data["duration"] = duration

    for field, value in update_data.items():
        setattr(time_track, field, value)

    db.add(time_track)
    db.commit()
    db.refresh(time_track)

    return time_track


@router.delete("/time/{time_track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_time_track(
        time_track_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> None:
    time_track = db.query(TimeTrack).filter(TimeTrack.id == time_track_id).first()

    if not time_track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time track not found",
        )

    # Check if time track's task belongs to user
    task = db.query(Task).filter(
        Task.id == time_track.task_id, Task.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    db.delete(time_track)
    db.commit()


@router.post("/tasks/{task_id}/time/start", response_model=TimeTrackSchema)
async def start_time_tracking(
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

    # Check if there's already an active time tracking
    active_tracking = (
        db.query(TimeTrack)
        .filter(TimeTrack.task_id == task_id, TimeTrack.end_time == None)
        .first()
    )

    if active_tracking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There's already active time tracking for this task",
        )

    time_track = TimeTrack(
        task_id=task_id,
        start_time=datetime.utcnow(),
    )

    db.add(time_track)
    db.commit()
    db.refresh(time_track)

    return time_track


@router.post("/tasks/{task_id}/time/stop", response_model=TimeTrackSchema)
async def stop_time_tracking(
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

    # Find active time tracking
    active_tracking = (
        db.query(TimeTrack)
        .filter(TimeTrack.task_id == task_id, TimeTrack.end_time == None)
        .first()
    )

    if not active_tracking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active time tracking found for this task",
        )

    # Set end time and calculate duration
    end_time = datetime.utcnow()
    duration = int((end_time - active_tracking.start_time).total_seconds())

    active_tracking.end_time = end_time
    active_tracking.duration = duration

    db.add(active_tracking)
    db.commit()
    db.refresh(active_tracking)

    return active_tracking
