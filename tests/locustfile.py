import json
import random
from datetime import datetime, timedelta
from typing import Dict

from locust import HttpUser, between, task


class TaskManagerUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        # Register a new user
        username = f"user_{random.randint(1, 10000)}"
        self.register_data = {
            "email": f"{username}@example.com",
            "username": username,
            "password": "password",
        }

        response = self.client.post(
            "/api/auth/register",
            json=self.register_data,
        )

        if response.status_code != 200:
            print(f"Failed to register user: {response.text}")
            return

        # Login to get token
        response = self.client.post(
            "/api/auth/token",
            data={
                "username": self.register_data["username"],
                "password": self.register_data["password"],
            },
        )

        if response.status_code != 200:
            print(f"Failed to login: {response.text}")
            return

        token_data = response.json()
        self.token = token_data["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

        # Create some initial tasks
        self.task_ids = []
        for i in range(3):
            task_data = self.create_random_task_data()
            response = self.client.post(
                "/api/tasks/",
                headers=self.headers,
                json=task_data,
            )

            if response.status_code == 200:
                self.task_ids.append(response.json()["id"])

    def create_random_task_data(self) -> Dict:
        priorities = ["low", "medium", "high", "urgent"]
        categories = ["personal", "work", "health", "education", "other"]

        return {
            "title": f"Task {random.randint(1, 1000)}",
            "description": f"Description {random.randint(1, 1000)}",
            "priority": random.choice(priorities),
            "category": random.choice(categories),
            "due_date": (datetime.utcnow() + timedelta(days=random.randint(1, 30))).isoformat(),
        }

    @task(3)
    def get_tasks(self):
        self.client.get("/api/tasks/", headers=self.headers)

    @task(1)
    def get_specific_task(self):
        if not self.task_ids:
            return

        task_id = random.choice(self.task_ids)
        self.client.get(f"/api/tasks/{task_id}", headers=self.headers)

    @task(2)
    def create_task(self):
        task_data = self.create_random_task_data()
        response = self.client.post(
            "/api/tasks/",
            headers=self.headers,
            json=task_data,
        )

        if response.status_code == 200:
            self.task_ids.append(response.json()["id"])

    @task(1)
    def update_task(self):
        if not self.task_ids:
            return

        task_id = random.choice(self.task_ids)
        update_data = {"title": f"Updated Task {random.randint(1, 1000)}"}

        self.client.put(
            f"/api/tasks/{task_id}",
            headers=self.headers,
            json=update_data,
        )

    @task(1)
    def delete_task(self):
        if not self.task_ids:
            return

        task_id = random.choice(self.task_ids)
        response = self.client.delete(
            f"/api/tasks/{task_id}",
            headers=self.headers,
        )

        if response.status_code == 204:
            self.task_ids.remove(task_id)

    @task(1)
    def create_time_track(self):
        if not self.task_ids:
            return

        task_id = random.choice(self.task_ids)
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        self.client.post(
            f"/api/tasks/{task_id}/time",
            headers=self.headers,
            json={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
        )

    @task(1)
    def create_reminder(self):
        if not self.task_ids:
            return

        task_id = random.choice(self.task_ids)
        reminder_time = datetime.utcnow() + timedelta(days=1)

        self.client.post(
            f"/api/tasks/{task_id}/reminders",
            headers=self.headers,
            json={
                "reminder_time": reminder_time.isoformat(),
            },
        )