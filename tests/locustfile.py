import json
import random
from datetime import datetime, timedelta
from typing import Dict

from locust import HttpUser, between, task


class TaskManagerUser(HttpUser):
    wait_time = between(1, 5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Инициализация атрибутов здесь, чтобы они всегда существовали
        self.token = ""
        self.headers = {}
        self.task_ids = []
        self.register_data = {}

    def on_start(self):
        # Register a new user
        try:
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
            for i in range(3):
                task_data = self.create_random_task_data()
                response = self.client.post(
                    "/api/tasks/",
                    headers=self.headers,
                    json=task_data,
                )

                if response.status_code == 200:
                    task_id = response.json().get("id")
                    if task_id:
                        self.task_ids.append(task_id)
        except Exception as e:
            print(f"Error in on_start: {str(e)}")

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
        if not self.headers:
            return
        self.client.get("/api/tasks/", headers=self.headers)

    @task(1)
    def get_specific_task(self):
        if not self.headers or not self.task_ids:
            return

        try:
            task_id = random.choice(self.task_ids)
            self.client.get(f"/api/tasks/{task_id}", headers=self.headers)
        except Exception as e:
            print(f"Error in get_specific_task: {str(e)}")

    @task(2)
    def create_task(self):
        if not self.headers:
            return

        try:
            task_data = self.create_random_task_data()
            response = self.client.post(
                "/api/tasks/",
                headers=self.headers,
                json=task_data,
            )

            if response.status_code == 200:
                task_id = response.json().get("id")
                if task_id:
                    self.task_ids.append(task_id)
        except Exception as e:
            print(f"Error in create_task: {str(e)}")

    @task(1)
    def update_task(self):
        if not self.headers or not self.task_ids:
            return

        try:
            task_id = random.choice(self.task_ids)
            update_data = {"title": f"Updated Task {random.randint(1, 1000)}"}

            self.client.put(
                f"/api/tasks/{task_id}",
                headers=self.headers,
                json=update_data,
            )
        except Exception as e:
            print(f"Error in update_task: {str(e)}")

    @task(1)
    def delete_task(self):
        if not self.headers or not self.task_ids:
            return

        try:
            task_id = random.choice(self.task_ids)
            response = self.client.delete(
                f"/api/tasks/{task_id}",
                headers=self.headers,
            )

            if response.status_code == 204 and task_id in self.task_ids:
                self.task_ids.remove(task_id)
        except Exception as e:
            print(f"Error in delete_task: {str(e)}")

    @task(1)
    def create_time_track(self):
        if not self.headers or not self.task_ids:
            return

        try:
            task_id = random.choice(self.task_ids)
            start_time = datetime.utcnow() - timedelta(hours=1)
            end_time = datetime.utcnow()

            self.client.post(
                f"/api/time-tracking/tasks/{task_id}/time",
                headers=self.headers,
                json={
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                },
            )
        except Exception as e:
            print(f"Error in create_time_track: {str(e)}")

    @task(1)
    def create_reminder(self):
        if not self.headers or not self.task_ids:
            return

        try:
            task_id = random.choice(self.task_ids)
            reminder_time = datetime.utcnow() + timedelta(days=1)

            self.client.post(
                f"/api/reminders/tasks/{task_id}",
                headers=self.headers,
                json={
                    "reminder_time": reminder_time.isoformat(),
                },
            )
        except Exception as e:
            print(f"Error in create_reminder: {str(e)}")