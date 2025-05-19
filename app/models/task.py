from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.db import Base


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELED = "canceled"


class TaskCategory(str, Enum):
    PERSONAL = "personal"
    WORK = "work"
    HEALTH = "health"
    EDUCATION = "education"
    OTHER = "other"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True)
    description = Column(Text, nullable=True)

    status = Column(SQLEnum(TaskStatus), default=TaskStatus.TODO)
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM)
    category = Column(SQLEnum(TaskCategory), default=TaskCategory.OTHER)

    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id"))

    # Relationships
    owner = relationship("User", back_populates="tasks")
    time_tracks = relationship("TimeTrack", back_populates="task")
    recurring_task = relationship("RecurringTask", back_populates="task", uselist=False)
    reminders = relationship("Reminder", back_populates="task")


class RecurringTask(Base):
    __tablename__ = "recurring_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), unique=True)

    # Recurrence patterns
    frequency = Column(String)  # daily, weekly, monthly, etc.
    interval = Column(Integer, default=1)  # every X days/weeks/etc.
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)

    # Relationships
    task = relationship("Task", back_populates="recurring_task")


class TimeTrack(Base):
    __tablename__ = "time_tracks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))

    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # in seconds

    # Relationships
    task = relationship("Task", back_populates="time_tracks")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))

    reminder_time = Column(DateTime)
    is_sent = Column(Boolean, default=False)

    # Relationships
    task = relationship("Task", back_populates="reminders")


class TelegramUser(Base):
    __tablename__ = "telegram_users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    telegram_id = Column(Integer, unique=True)
    chat_id = Column(Integer, unique=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="telegram_user")