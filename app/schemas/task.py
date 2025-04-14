from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.task import TaskCategory, TaskPriority, TaskStatus


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    category: TaskCategory = TaskCategory.OTHER
    due_date: Optional[datetime] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    category: Optional[TaskCategory] = None
    due_date: Optional[datetime] = None


class TaskInDB(TaskBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class Task(TaskInDB):
    pass


# RecurringTask schemas
class RecurringTaskBase(BaseModel):
    frequency: str
    interval: int = 1
    start_date: datetime
    end_date: Optional[datetime] = None


class RecurringTaskCreate(RecurringTaskBase):
    pass


class RecurringTaskUpdate(BaseModel):
    frequency: Optional[str] = None
    interval: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class RecurringTaskInDB(RecurringTaskBase):
    id: int
    task_id: int

    class Config:
        orm_mode = True


class RecurringTask(RecurringTaskInDB):
    pass


# TimeTrack schemas
class TimeTrackBase(BaseModel):
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[int] = None  # in seconds


class TimeTrackCreate(TimeTrackBase):
    pass


class TimeTrackUpdate(BaseModel):
    end_time: Optional[datetime] = None
    duration: Optional[int] = None


class TimeTrackInDB(TimeTrackBase):
    id: int
    task_id: int

    class Config:
        orm_mode = True


class TimeTrack(TimeTrackInDB):
    pass


# Reminder schemas
class ReminderBase(BaseModel):
    reminder_time: datetime
    is_sent: bool = False


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    reminder_time: Optional[datetime] = None
    is_sent: Optional[bool] = None


class ReminderInDB(ReminderBase):
    id: int
    task_id: int

    class Config:
        orm_mode = True


class Reminder(ReminderInDB):
    pass


# TelegramUser schemas
class TelegramUserBase(BaseModel):
    telegram_id: int
    chat_id: int
    is_active: bool = True


class TelegramUserCreate(TelegramUserBase):
    pass


class TelegramUserUpdate(BaseModel):
    telegram_id: Optional[int] = None
    chat_id: Optional[int] = None
    is_active: Optional[bool] = None


class TelegramUserInDB(TelegramUserBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True


class TelegramUser(TelegramUserInDB):
    pass