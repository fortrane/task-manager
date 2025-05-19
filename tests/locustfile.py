import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from locust import HttpUser, between, task


class TaskManagerUser(HttpUser):
    # Увеличиваем время ожидания для снижения интенсивности
    wait_time = between(1.5, 5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = ""
        self.headers = {}
        self.task_ids = []
        self.time_track_ids = []
        self.reminder_ids = []
        self.recurring_task_ids = []
        self.register_data = {}
        self.max_entities = 15  # Ограничиваем максимальное количество создаваемых сущностей
        self.last_created_task_id = None  # Для коррелированных запросов

    def on_start(self):
        """Регистрация пользователя и создание начальных задач"""
        try:
            # Добавляем паузу перед регистрацией для распределения нагрузки
            time.sleep(random.uniform(0.2, 0.5))

            username = f"user_{random.randint(1, 1000000)}"
            self.register_data = {
                "email": f"{username}@example.com",
                "username": username,
                "password": "password123",
            }

            # Регистрация пользователя
            response = self.client.post(
                "/api/auth/register",
                json=self.register_data,
                name="/api/auth/register",
                catch_response=True
            )

            if response.status_code != 200:
                response.failure(f"Failed to register user: {response.text}")
                return

            # Небольшая пауза между запросами
            time.sleep(random.uniform(0.1, 0.3))

            # Аутентификация и получение токена
            response = self.client.post(
                "/api/auth/token",
                data={
                    "username": self.register_data["username"],
                    "password": self.register_data["password"],
                },
                name="/api/auth/token",
                catch_response=True
            )

            if response.status_code != 200:
                response.failure(f"Failed to login: {response.text}")
                return

            token_data = response.json()
            self.token = token_data["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}

            # Создание начальных задач с разными параметрами
            task_categories = ["personal", "work", "health", "education", "other"]
            task_priorities = ["low", "medium", "high", "urgent"]
            task_statuses = ["todo", "in_progress", "done", "canceled"]

            # Создаем ограниченное число начальных задач
            for i in range(min(5, self.max_entities)):
                # Пауза между созданием начальных задач
                time.sleep(random.uniform(0.2, 0.5))

                task_data = {
                    "title": f"Initial Task {random.randint(1, 10000)}",
                    "description": f"Description for task {random.randint(1, 10000)}",
                    "priority": random.choice(task_priorities),
                    "category": random.choice(task_categories),
                    "status": random.choice(task_statuses),
                    "due_date": (datetime.utcnow() + timedelta(days=random.randint(1, 30))).isoformat(),
                }

                response = self.client.post(
                    "/api/tasks/",
                    headers=self.headers,
                    json=task_data,
                    name="/api/tasks/ (create initial)",
                    catch_response=True
                )

                if response.status_code == 200:
                    task_id = response.json().get("id")
                    if task_id:
                        self.task_ids.append(task_id)
        except Exception as e:
            print(f"Error in on_start: {str(e)}")
            time.sleep(1)  # Пауза в случае ошибки для стабилизации

    def on_stop(self):
        """Очистка созданных ресурсов"""
        try:
            # Удаляем часть созданных задач для очистки БД
            for task_id in list(self.task_ids):
                try:
                    # Ограничиваем число удалений для сокращения нагрузки
                    if random.random() < 0.3:  # Удаляем примерно 30% задач
                        self.client.delete(
                            f"/api/tasks/{task_id}",
                            headers=self.headers,
                            name="/api/tasks/{id} (cleanup)",
                            catch_response=True
                        )
                        self.task_ids.remove(task_id)
                except Exception:
                    pass
        except Exception as e:
            print(f"Error in on_stop: {str(e)}")

    @task(8)
    def get_tasks(self):
        """Получение списка задач с различными фильтрами"""
        if not self.headers:
            return

        try:
            # Небольшая пауза перед запросом
            time.sleep(random.uniform(0.1, 0.3))

            # Различные фильтры для более разнообразной нагрузки
            filters = [
                {},  # без фильтров
                {"status": "todo"},
                {"priority": "high"},
                {"category": "work"},
                {"status": "in_progress", "priority": "urgent"}
            ]

            selected_filter = random.choice(filters)
            query_params = "&".join([f"{key}={value}" for key, value in selected_filter.items()])
            url = f"/api/tasks/?{query_params}" if query_params else "/api/tasks/"

            with self.client.get(
                    url,
                    headers=self.headers,
                    name="/api/tasks/ (get list)",
                    catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Failed to get tasks: {response.text}")
        except Exception as e:
            print(f"Error in get_tasks: {str(e)}")
            time.sleep(0.5)  # Пауза при ошибке

    @task(4)
    def get_specific_task(self):
        """Получение конкретной задачи"""
        if not self.headers or not self.task_ids:
            return

        try:
            # Небольшая пауза перед запросом
            time.sleep(random.uniform(0.1, 0.2))

            task_id = random.choice(self.task_ids)
            with self.client.get(
                    f"/api/tasks/{task_id}",
                    headers=self.headers,
                    name="/api/tasks/{id} (get one)",
                    catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Failed to get task: {response.text}")
                else:
                    # Сохраняем ID последней полученной задачи для коррелированных запросов
                    self.last_created_task_id = task_id
        except Exception as e:
            print(f"Error in get_specific_task: {str(e)}")
            time.sleep(0.5)

    @task(5)
    def create_task(self):
        """Создание новой задачи"""
        if not self.headers or len(self.task_ids) >= self.max_entities:
            return

        try:
            # Небольшая пауза перед запросом
            time.sleep(random.uniform(0.2, 0.4))

            # Создаем разнообразные задачи
            task_categories = ["personal", "work", "health", "education", "other"]
            task_priorities = ["low", "medium", "high", "urgent"]

            task_data = {
                "title": f"New Task {random.randint(1, 10000)}",
                "description": f"Created during stress test {random.randint(1, 10000)}",
                "priority": random.choice(task_priorities),
                "category": random.choice(task_categories),
                "due_date": (datetime.utcnow() + timedelta(days=random.randint(1, 30))).isoformat(),
            }

            with self.client.post(
                    "/api/tasks/",
                    headers=self.headers,
                    json=task_data,
                    name="/api/tasks/ (create)",
                    catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Failed to create task: {response.text}")
                else:
                    task_id = response.json().get("id")
                    if task_id:
                        self.task_ids.append(task_id)
                        self.last_created_task_id = task_id
        except Exception as e:
            print(f"Error in create_task: {str(e)}")
            time.sleep(0.5)

    @task(6)
    def update_task(self):
        """Обновление задачи"""
        if not self.headers or not self.task_ids:
            return

        try:
            # Небольшая пауза перед запросом
            time.sleep(random.uniform(0.1, 0.3))

            # Предпочитаем обновлять последнюю созданную/полученную задачу, если она есть
            task_id = self.last_created_task_id if self.last_created_task_id and self.last_created_task_id in self.task_ids else random.choice(
                self.task_ids)

            # Разнообразные обновления
            update_options = [
                {"title": f"Updated Task {random.randint(1, 10000)}"},
                {"description": f"Updated description {random.randint(1, 10000)}"},
                {"status": random.choice(["todo", "in_progress", "done", "canceled"])},
                {"priority": random.choice(["low", "medium", "high", "urgent"])},
                {"category": random.choice(["personal", "work", "health", "education", "other"])},
                {
                    "title": f"Multi-updated Task {random.randint(1, 10000)}",
                    "status": random.choice(["todo", "in_progress", "done", "canceled"]),
                    "priority": random.choice(["low", "medium", "high", "urgent"])
                }
            ]

            update_data = random.choice(update_options)

            with self.client.put(
                    f"/api/tasks/{task_id}",
                    headers=self.headers,
                    json=update_data,
                    name="/api/tasks/{id} (update)",
                    catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Failed to update task: {response.text}")
        except Exception as e:
            print(f"Error in update_task: {str(e)}")
            time.sleep(0.5)

    @task(1)
    def delete_task(self):
        """Удаление задачи"""
        if not self.headers or not self.task_ids or len(self.task_ids) <= 2:  # Оставляем хотя бы 2 задачи
            return

        try:
            # Небольшая пауза перед запросом
            time.sleep(random.uniform(0.2, 0.5))

            task_id = random.choice(self.task_ids)
            with self.client.delete(
                    f"/api/tasks/{task_id}",
                    headers=self.headers,
                    name="/api/tasks/{id} (delete)",
                    catch_response=True
            ) as response:
                if response.status_code == 204 and task_id in self.task_ids:
                    self.task_ids.remove(task_id)
                    # Если удалена последняя сохраненная задача, сбрасываем её
                    if task_id == self.last_created_task_id:
                        self.last_created_task_id = None
                elif response.status_code != 204:
                    response.failure(f"Failed to delete task: {response.status_code}")
        except Exception as e:
            print(f"Error in delete_task: {str(e)}")
            time.sleep(0.5)

    @task(3)
    def create_time_track(self):
        """Создание трека времени"""
        if not self.headers or not self.task_ids or len(self.time_track_ids) >= self.max_entities:
            return

        try:
            # Небольшая пауза перед запросом
            time.sleep(random.uniform(0.2, 0.4))

            task_id = random.choice(self.task_ids)

            # Разные варианты треков времени
            track_options = [
                # Завершенный трек
                {
                    "start_time": (datetime.utcnow() - timedelta(hours=random.randint(1, 5))).isoformat(),
                    "end_time": datetime.utcnow().isoformat()
                },
                # Только начало
                {
                    "start_time": datetime.utcnow().isoformat()
                }
            ]

            track_data = random.choice(track_options)

            with self.client.post(
                    f"/api/time-tracking/tasks/{task_id}/time",
                    headers=self.headers,
                    json=track_data,
                    name="/api/time-tracking/tasks/{id}/time (create)",
                    catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Failed to create time track: {response.text}")
                else:
                    time_track_id = response.json().get("id")
                    if time_track_id:
                        self.time_track_ids.append(time_track_id)
        except Exception as e:
            print(f"Error in create_time_track: {str(e)}")
            time.sleep(0.5)

    @task(2)
    def get_time_tracks(self):
        """Получение треков времени"""
        if not self.headers or not self.task_ids:
            return

        try:
            # Небольшая пауза перед запросом
            time.sleep(random.uniform(0.1, 0.3))

            task_id = random.choice(self.task_ids)
            with self.client.get(
                    f"/api/time-tracking/tasks/{task_id}/time",
                    headers=self.headers,
                    name="/api/time-tracking/tasks/{id}/time (get list)",
                    catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Failed to get time tracks: {response.text}")
        except Exception as e:
            print(f"Error in get_time_tracks: {str(e)}")
            time.sleep(0.5)

    @task(2)
    def create_reminder(self):
        """Создание напоминания"""
        if not self.headers or not self.task_ids or len(self.reminder_ids) >= self.max_entities:
            return

        try:
            # Небольшая пауза перед запросом
            time.sleep(random.uniform(0.2, 0.4))

            task_id = random.choice(self.task_ids)
            reminder_time = datetime.utcnow() + timedelta(days=random.randint(1, 14))

            with self.client.post(
                    f"/api/reminders/tasks/{task_id}",
                    headers=self.headers,
                    json={
                        "reminder_time": reminder_time.isoformat(),
                    },
                    name="/api/reminders/tasks/{id} (create)",
                    catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Failed to create reminder: {response.text}")
                else:
                    reminder_id = response.json().get("id")
                    if reminder_id:
                        self.reminder_ids.append(reminder_id)
        except Exception as e:
            print(f"Error in create_reminder: {str(e)}")
            time.sleep(0.5)

    @task(2)
    def get_reminders(self):
        """Получение напоминаний"""
        if not self.headers or not self.task_ids:
            return

        try:
            # Небольшая пауза перед запросом
            time.sleep(random.uniform(0.1, 0.3))

            task_id = random.choice(self.task_ids)
            with self.client.get(
                    f"/api/reminders/tasks/{task_id}",
                    headers=self.headers,
                    name="/api/reminders/tasks/{id} (get list)",
                    catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Failed to get reminders: {response.text}")
        except Exception as e:
            print(f"Error in get_reminders: {str(e)}")
            time.sleep(0.5)

    @task(1)
    def create_recurring_task(self):
        """Создание повторяющейся задачи"""
        if not self.headers or not self.task_ids or len(self.recurring_task_ids) >= self.max_entities // 2:
            return

        try:
            # Находим задачи, которые ещё не являются повторяющимися
            non_recurring_tasks = [tid for tid in self.task_ids if tid not in self.recurring_task_ids]

            if not non_recurring_tasks:
                return

            # Небольшая пауза перед запросом
            time.sleep(random.uniform(0.2, 0.5))

            # Выбираем случайную задачу из не повторяющихся
            task_id = random.choice(non_recurring_tasks)

            frequencies = ["daily", "weekly", "monthly"]
            start_date = datetime.utcnow()

            with self.client.post(
                    f"/api/tasks/{task_id}/recurring",
                    headers=self.headers,
                    json={
                        "frequency": random.choice(frequencies),
                        "interval": random.randint(1, 4),
                        "start_date": start_date.isoformat()
                    },
                    name="/api/tasks/{id}/recurring (create)",
                    catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Failed to create recurring task: {response.text}")
                else:
                    self.recurring_task_ids.append(task_id)
        except Exception as e:
            print(f"Error in create_recurring_task: {str(e)}")
            time.sleep(0.5)

    @task(1)
    def user_profile(self):
        """Получение профиля пользователя"""
        if not self.headers:
            return

        try:
            # Небольшая пауза перед запросом
            time.sleep(random.uniform(0.1, 0.2))

            with self.client.get(
                    "/api/auth/me",
                    headers=self.headers,
                    name="/api/auth/me",
                    catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Failed to get user profile: {response.text}")
        except Exception as e:
            print(f"Error in user_profile: {str(e)}")
            time.sleep(0.5)

    # Корреляционные последовательности запросов
    @task(3)
    def create_and_update_task(self):
        """Создание и затем обновление задачи"""
        if not self.headers or len(self.task_ids) >= self.max_entities:
            return

        try:
            # Создаем задачу
            time.sleep(random.uniform(0.2, 0.3))
            task_data = {
                "title": f"Correlated Task {random.randint(1, 10000)}",
                "description": f"Task for correlated operations",
                "priority": "medium",
                "category": "work",
                "due_date": (datetime.utcnow() + timedelta(days=5)).isoformat(),
            }

            create_response = self.client.post(
                "/api/tasks/",
                headers=self.headers,
                json=task_data,
                name="/api/tasks/ (correlated create)",
                catch_response=True
            )

            if create_response.status_code != 200:
                create_response.failure(f"Failed correlated create: {create_response.text}")
                return

            task_id = create_response.json().get("id")
            if not task_id:
                return

            self.task_ids.append(task_id)
            self.last_created_task_id = task_id

            # Короткая пауза между созданием и обновлением
            time.sleep(random.uniform(0.1, 0.2))

            # Обновляем созданную задачу
            update_data = {
                "status": "in_progress",
                "priority": "high",
            }

            update_response = self.client.put(
                f"/api/tasks/{task_id}",
                headers=self.headers,
                json=update_data,
                name="/api/tasks/{id} (correlated update)",
                catch_response=True
            )

            if update_response.status_code != 200:
                update_response.failure(f"Failed correlated update: {update_response.text}")
        except Exception as e:
            print(f"Error in create_and_update_task: {str(e)}")
            time.sleep(0.5)

    @task(2)
    def create_with_reminder(self):
        """Создание задачи и добавление к ней напоминания"""
        if not self.headers or len(self.task_ids) >= self.max_entities:
            return

        try:
            # Создаем задачу
            time.sleep(random.uniform(0.2, 0.3))
            task_data = {
                "title": f"Task with Reminder {random.randint(1, 10000)}",
                "description": f"Task that will have a reminder",
                "priority": "high",
                "category": "personal",
                "due_date": (datetime.utcnow() + timedelta(days=3)).isoformat(),
            }

            create_response = self.client.post(
                "/api/tasks/",
                headers=self.headers,
                json=task_data,
                name="/api/tasks/ (with reminder create)",
                catch_response=True
            )

            if create_response.status_code != 200:
                create_response.failure(f"Failed create with reminder: {create_response.text}")
                return

            task_id = create_response.json().get("id")
            if not task_id:
                return

            self.task_ids.append(task_id)

            # Короткая пауза между созданием задачи и добавлением напоминания
            time.sleep(random.uniform(0.1, 0.2))

            # Добавляем напоминание
            reminder_data = {
                "reminder_time": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            }

            reminder_response = self.client.post(
                f"/api/reminders/tasks/{task_id}",
                headers=self.headers,
                json=reminder_data,
                name="/api/reminders/tasks/{id} (correlated create)",
                catch_response=True
            )

            if reminder_response.status_code != 200:
                reminder_response.failure(f"Failed create reminder: {reminder_response.text}")
            else:
                reminder_id = reminder_response.json().get("id")
                if reminder_id:
                    self.reminder_ids.append(reminder_id)
        except Exception as e:
            print(f"Error in create_with_reminder: {str(e)}")
            time.sleep(0.5)