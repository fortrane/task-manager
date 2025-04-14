from datetime import datetime, timedelta
from typing import Dict, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import Task, TaskCategory, TaskPriority, TaskStatus, User

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
def test_task(db_session: Session, test_user: User) -> Task:
    task = Task(
        title="Test Task",
        description="Test Description",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        category=TaskCategory.WORK,
        due_date=datetime.utcnow() + timedelta(days=1),
        owner_id=test_user.id,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    return task


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
        client: TestClient, user_token_headers: Dict[str, str], test_task: Task
):
    response = client.get("/api/tasks/", headers=user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(task["title"] == "Test Task" for task in data)


def test_read_task(
        client: TestClient, user_token_headers: Dict[str, str], test_task: Task
):
    response = client.get(
        f"/api/tasks/{test_task.id}", headers=user_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["description"] == "Test Description"


def test_update_task(
        client: TestClient, user_token_headers: Dict[str, str], test_task: Task
):
    response = client.put(
        f"/api/tasks/{test_task.id}",
        headers=user_token_headers,
        json={"title": "Updated Task"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Task"
    assert data["description"] == "Test Description"  # unchanged


def test_delete_task(
        client: TestClient, user_token_headers: Dict[str, str], test_task: Task
):
    response = client.delete(
        f"/api/tasks/{test_task.id}", headers=user_token_headers
    )
    assert response.status_code == 204

    # Verify it's deleted
    response = client.get(
        f"/api/tasks/{test_task.id}", headers=user_token_headers
    )
    assert response.status_code == 404