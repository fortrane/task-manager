import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

# Define metrics
REQUEST_COUNT = Counter(
    "app_request_count",
    "Application Request Count",
    ["app_name", "method", "endpoint", "http_status"],
)

REQUEST_LATENCY = Histogram(
    "app_request_latency_seconds",
    "Application Request Latency",
    ["app_name", "method", "endpoint"],
)

# Task metrics
TASK_CREATED_COUNT = Counter(
    "app_task_created_total",
    "Total number of tasks created",
    ["category", "priority"],
)

TASK_COMPLETED_COUNT = Counter(
    "app_task_completed_total",
    "Total number of tasks completed",
    ["category", "priority"],
)

TASK_COMPLETION_TIME = Histogram(
    "app_task_completion_time_seconds",
    "Time taken to complete tasks",
    ["category", "priority"],
)

# Telegram metrics
TELEGRAM_NOTIFICATION_COUNT = Counter(
    "app_telegram_notifications_total",
    "Total number of Telegram notifications sent",
    ["status"],
)


# Middleware for HTTP request metrics
class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        response = await call_next(request)

        request_latency = time.time() - start_time
        REQUEST_LATENCY.labels(
            app_name="task_manager",
            method=request.method,
            endpoint=request.url.path,
        ).observe(request_latency)

        REQUEST_COUNT.labels(
            app_name="task_manager",
            method=request.method,
            endpoint=request.url.path,
            http_status=response.status_code,
        ).inc()

        return response


# Helper functions for task metrics
def record_task_created(category: str, priority: str) -> None:
    TASK_CREATED_COUNT.labels(category=category, priority=priority).inc()


def record_task_completed(category: str, priority: str, duration_seconds: float) -> None:
    TASK_COMPLETED_COUNT.labels(category=category, priority=priority).inc()
    TASK_COMPLETION_TIME.labels(category=category, priority=priority).observe(duration_seconds)


# Helper functions for Telegram metrics
def record_telegram_notification(status: str) -> None:
    TELEGRAM_NOTIFICATION_COUNT.labels(status=status).inc()