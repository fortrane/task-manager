from fastapi import APIRouter
from app.api.endpoints import auth, tasks, reminders, time_tracking, telegram

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(reminders.router, prefix="/reminders", tags=["Reminders"])
api_router.include_router(time_tracking.router, prefix="/time-tracking", tags=["Time Tracking"])
api_router.include_router(telegram.router, prefix="/telegram", tags=["Telegram Integration"])