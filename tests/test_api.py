from datetime import datetime, timedelta
from typing import Dict, Generator, List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base, get_db
from app.core.security import create_access_token, get_password_hash

import sys
import os
sys.path.append("/app")
from main import app

from app.models import (Reminder, Task, TaskCategory, TaskPriority, TaskStatus,
                        TimeTrack, User, RecurringTask, TelegramUser)
from app.utils.metrics import record_task_created, record_task_completed

# Setup test database
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Override the dependency to use test db
def override_get_db() -> Generator[Session, None, None]:
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client() -> Generator:
    # Create the test database and tables
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as test_client:
        yield test_client

    # Clean up after test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_user(db_session: Session) -> User:
    user = db_session.query(User).filter(User.email == "test@example.com").first()
    if not user:
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=get_password_hash("password"),
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    return user


@pytest.fixture
def test_tasks(db_session: Session, test_user: User) -> List[Task]:
    # Создаем набор разных задач для более полного тестирования
    tasks = []
    categories = [TaskCategory.WORK, TaskCategory.PERSONAL, TaskCategory.HEALTH, TaskCategory.EDUCATION,
                  TaskCategory.OTHER]
    priorities = [TaskPriority.LOW, TaskPriority.MEDIUM, TaskPriority.HIGH, TaskPriority.URGENT]
    statuses = [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.DONE, TaskStatus.CANCELED]

    # Создаем по одной задаче каждой категории, приоритета и статуса
    for i, (category, priority, status) in enumerate(zip(categories, priorities, statuses)):
        task = Task(
            title=f"Test Task {i + 1}",
            description=f"Test Description {i + 1}",
            status=status,
            priority=priority,
            category=category,
            due_date=datetime.utcnow() + timedelta(days=i + 1),
            owner_id=test_user.id,
        )
        db_session.add(task)

    db_session.commit()

    # Получаем все задачи пользователя
    tasks = db_session.query(Task).filter(Task.owner_id == test_user.id).all()
    return tasks


@pytest.fixture
def test_time_track(db_session: Session, test_tasks: List[Task]) -> TimeTrack:
    task = test_tasks[0]  # Берем первую задачу

    time_track = TimeTrack(
        task_id=task.id,
        start_time=datetime.utcnow() - timedelta(hours=1),
        end_time=datetime.utcnow(),
        duration=3600  # 1 час в секундах
    )

    db_session.add(time_track)
    db_session.commit()
    db_session.refresh(time_track)

    return time_track


@pytest.fixture
def test_reminder(db_session: Session, test_tasks: List[Task]) -> Reminder:
    task = test_tasks[0]  # Берем первую задачу

    reminder = Reminder(
        task_id=task.id,
        reminder_time=datetime.utcnow() + timedelta(days=1),
        is_sent=False
    )

    db_session.add(reminder)
    db_session.commit()
    db_session.refresh(reminder)

    return reminder


@pytest.fixture
def test_recurring_task(db_session: Session, test_tasks: List[Task]) -> RecurringTask:
    task = test_tasks[0]  # Берем первую задачу

    recurring_task = RecurringTask(
        task_id=task.id,
        frequency="weekly",
        interval=1,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=90)
    )

    db_session.add(recurring_task)
    db_session.commit()
    db_session.refresh(recurring_task)

    return recurring_task


@pytest.fixture
def test_telegram_user(db_session: Session, test_user: User) -> TelegramUser:
    telegram_user = TelegramUser(
        user_id=test_user.id,
        telegram_id=123456789,
        chat_id=123456789,
        is_active=True
    )

    db_session.add(telegram_user)
    db_session.commit()
    db_session.refresh(telegram_user)

    return telegram_user


@pytest.fixture
def user_token_headers(test_user: User) -> Dict[str, str]:
    access_token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {access_token}"}


def test_read_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Task Manager API is running"}


def test_create_user(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "password",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["username"] == "newuser"
    assert "id" in data


def test_login(client: TestClient, test_user: User):
    response = client.post(
        "/api/auth/token",
        data={"username": test_user.username, "password": "password"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_read_users_me(client: TestClient, user_token_headers: Dict[str, str]):
    response = client.get("/api/auth/me", headers=user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"


def test_create_task(client: TestClient, user_token_headers: Dict[str, str]):
    response = client.post(
        "/api/tasks/",
        headers=user_token_headers,
        json={
            "title": "New Task",
            "description": "New Description",
            "status": "todo",
            "priority": "high",
            "category": "personal",
            "due_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Task"
    assert data["description"] == "New Description"
    assert data["status"] == "todo"
    assert data["priority"] == "high"
    assert data["category"] == "personal"


def test_read_tasks(
        client: TestClient, user_token_headers: Dict[str, str], test_tasks: List[Task]
):
    response = client.get("/api/tasks/", headers=user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= len(test_tasks)
    # Проверяем, что все наши тестовые задачи присутствуют в ответе
    task_titles = [task["title"] for task in data]
    for test_task in test_tasks:
        assert test_task.title in task_titles


def test_read_task(
        client: TestClient, user_token_headers: Dict[str, str], test_tasks: List[Task]
):
    task = test_tasks[0]  # Берем первую задачу
    response = client.get(
        f"/api/tasks/{task.id}", headers=user_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == task.title
    assert data["description"] == task.description


def test_update_task(
        client: TestClient, user_token_headers: Dict[str, str], test_tasks: List[Task]
):
    task = test_tasks[0]  # Берем первую задачу
    response = client.put(
        f"/api/tasks/{task.id}",
        headers=user_token_headers,
        json={"title": "Updated Task", "status": "in_progress"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Task"
    assert data["status"] == "in_progress"
    assert data["description"] == task.description  # unchanged


def test_complete_task(
        client: TestClient, user_token_headers: Dict[str, str], test_tasks: List[Task]
):
    task = test_tasks[0]  # Берем первую задачу
    response = client.put(
        f"/api/tasks/{task.id}",
        headers=user_token_headers,
        json={"status": "done"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "done"
    assert data["completed_at"] is not None


def test_filter_tasks_by_status(
        client: TestClient, user_token_headers: Dict[str, str], test_tasks: List[Task]
):
    response = client.get(
        "/api/tasks/?status=todo",
        headers=user_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    for task in data:
        assert task["status"] == "todo"


def test_filter_tasks_by_priority(
        client: TestClient, user_token_headers: Dict[str, str], test_tasks: List[Task]
):
    response = client.get(
        "/api/tasks/?priority=high",
        headers=user_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    for task in data:
        assert task["priority"] == "high"


def test_filter_tasks_by_category(
        client: TestClient, user_token_headers: Dict[str, str], test_tasks: List[Task]
):
    response = client.get(
        "/api/tasks/?category=work",
        headers=user_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    for task in data:
        assert task["category"] == "work"


def test_delete_task(
        client: TestClient, user_token_headers: Dict[str, str], test_tasks: List[Task]
):
    task = test_tasks[0]  # Берем первую задачу
    response = client.delete(
        f"/api/tasks/{task.id}", headers=user_token_headers
    )
    assert response.status_code == 204

    # Проверяем, что задача удалена
    response = client.get(
        f"/api/tasks/{task.id}", headers=user_token_headers
    )
    assert response.status_code == 404


def test_create_time_track(
        client: TestClient, user_token_headers: Dict[str, str], test_tasks: List[Task]
):
    task = test_tasks[0]  # Берем первую задачу
    start_time = datetime.utcnow() - timedelta(hours=1)
    end_time = datetime.utcnow()

    response = client.post(
        f"/api/time-tracking/tasks/{task.id}/time",
        headers=user_token_headers,
        json={
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task.id
    assert "duration" in data
    assert data["duration"] > 0


def test_start_time_tracking(
        client: TestClient, user_token_headers: Dict[str, str], test_tasks: List[Task]
):
    task = test_tasks[1]  # Берем вторую задачу

    response = client.post(
        f"/api/time-tracking/tasks/{task.id}/time/start",
        headers=user_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task.id
    assert data["start_time"] is not None
    assert data["end_time"] is None


def test_stop_time_tracking(
        client: TestClient, user_token_headers: Dict[str, str], test_tasks: List[Task], db_session: Session
):
    task = test_tasks[2]  # Берем третью задачу

    # Сначала создаем активный трекинг времени
    time_track = TimeTrack(
        task_id=task.id,
        start_time=datetime.utcnow() - timedelta(minutes=30),
    )
    db_session.add(time_track)
    db_session.commit()

    response = client.post(
        f"/api/time-tracking/tasks/{task.id}/time/stop",
        headers=user_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task.id
    assert data["start_time"] is not None
    assert data["end_time"] is not None
    assert data["duration"] > 0


def test_get_time_tracks(
        client: TestClient, user_token_headers: Dict[str, str], test_tasks: List[Task], test_time_track: TimeTrack
):
    task = test_tasks[0]  # Берем первую задачу

    response = client.get(
        f"/api/time-tracking/tasks/{task.id}/time",
        headers=user_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["task_id"] == task.id


def test_create_reminder(
        client: TestClient, user_token_headers: Dict[str, str], test_tasks: List[Task]
):
    task = test_tasks[0]  # Берем первую задачу
    reminder_time = datetime.utcnow() + timedelta(days=1)

    response = client.post(
        f"/api/reminders/tasks/{task.id}",
        headers=user_token_headers,
        json={
            "reminder_time": reminder_time.isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task.id
    assert data["reminder_time"] is not None
    assert data["is_sent"] is False


def test_get_reminders(
        client: TestClient, user_token_headers: Dict[str, str], test_tasks: List[Task], test_reminder: Reminder
):
    task = test_tasks[0]  # Берем первую задачу

    response = client.get(
        f"/api/reminders/tasks/{task.id}",
        headers=user_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["task_id"] == task.id


def test_update_reminder(
        client: TestClient, user_token_headers: Dict[str, str], test_reminder: Reminder
):
    new_reminder_time = datetime.utcnow() + timedelta(days=2)

    response = client.put(
        f"/api/reminders/update/{test_reminder.id}",
        headers=user_token_headers,
        json={
            "reminder_time": new_reminder_time.isoformat(),
            "is_sent": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_reminder.id
    assert data["is_sent"] is True


def test_delete_reminder(
        client: TestClient, user_token_headers: Dict[str, str], test_reminder: Reminder
):
    response = client.delete(
        f"/api/reminders/delete/{test_reminder.id}",
        headers=user_token_headers,
    )
    assert response.status_code == 204


def test_create_recurring_task(
        client: TestClient, user_token_headers: Dict[str, str], test_tasks: List[Task]
):
    task = test_tasks[1]  # Берем вторую задачу

    response = client.post(
        f"/api/tasks/{task.id}/recurring",
        headers=user_token_headers,
        json={
            "frequency": "weekly",
            "interval": 1,
            "start_date": datetime.utcnow().isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task.id
    assert data["frequency"] == "weekly"
    assert data["interval"] == 1


def test_get_recurring_task(
        client: TestClient, user_token_headers: Dict[str, str], test_recurring_task: RecurringTask
):
    response = client.get(
        f"/api/tasks/{test_recurring_task.task_id}/recurring",
        headers=user_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == test_recurring_task.task_id
    assert data["frequency"] == test_recurring_task.frequency


def test_update_recurring_task(
        client: TestClient, user_token_headers: Dict[str, str], test_recurring_task: RecurringTask
):
    response = client.put(
        f"/api/tasks/{test_recurring_task.task_id}/recurring",
        headers=user_token_headers,
        json={
            "frequency": "monthly",
            "interval": 2,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["frequency"] == "monthly"
    assert data["interval"] == 2


def test_delete_recurring_task(
        client: TestClient, user_token_headers: Dict[str, str], test_recurring_task: RecurringTask
):
    response = client.delete(
        f"/api/tasks/{test_recurring_task.task_id}/recurring",
        headers=user_token_headers,
    )
    assert response.status_code == 204


def test_connect_telegram(
        client: TestClient, user_token_headers: Dict[str, str], test_user: User
):
    response = client.post(
        "/api/telegram/connect",
        headers=user_token_headers,
        json={
            "telegram_id": 987654321,
            "chat_id": 987654321,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == test_user.id
    assert data["telegram_id"] == 987654321
    assert data["chat_id"] == 987654321
    assert data["is_active"] is True


def test_get_telegram_connection(
        client: TestClient, user_token_headers: Dict[str, str], test_telegram_user: TelegramUser
):
    response = client.get(
        "/api/telegram/connection",
        headers=user_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == test_telegram_user.user_id
    assert data["telegram_id"] == test_telegram_user.telegram_id
    assert data["chat_id"] == test_telegram_user.chat_id


def test_update_telegram_connection(
        client: TestClient, user_token_headers: Dict[str, str], test_telegram_user: TelegramUser
):
    response = client.put(
        "/api/telegram/connection",
        headers=user_token_headers,
        json={
            "is_active": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False


def test_delete_telegram_connection(
        client: TestClient, user_token_headers: Dict[str, str], test_telegram_user: TelegramUser
):
    response = client.delete(
        "/api/telegram/connection",
        headers=user_token_headers,
    )
    assert response.status_code == 204