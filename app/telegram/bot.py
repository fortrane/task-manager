import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from prometheus_client import start_http_server
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import Reminder, Task, TelegramUser, User
from app.utils.metrics import record_telegram_notification

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = Router()


# Function to get DB session
def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


# Function to get user by Telegram ID
def get_user_by_telegram_id(telegram_id: int, db: Session) -> Optional[User]:
    telegram_user = (
        db.query(TelegramUser)
        .filter(TelegramUser.telegram_id == telegram_id)
        .first()
    )

    if not telegram_user:
        return None

    user = db.query(User).filter(User.id == telegram_user.user_id).first()
    return user


# Function to format task message
def format_task_message(task: Task) -> str:
    status_emoji = {
        "todo": "🔲",
        "in_progress": "🔄",
        "done": "✅",
        "canceled": "❌",
    }

    priority_emoji = {
        "low": "⬇️",
        "medium": "➡️",
        "high": "⬆️",
        "urgent": "🔥",
    }

    category_emoji = {
        "personal": "👤",
        "work": "💼",
        "health": "🏥",
        "education": "📚",
        "other": "📋",
    }

    due_date_str = f"Due: {task.due_date.strftime('%Y-%m-%d %H:%M')}" if task.due_date else "No due date"

    message = (
        f"{status_emoji.get(task.status.value, '🔲')} "
        f"{priority_emoji.get(task.priority.value, '➡️')} "
        f"{category_emoji.get(task.category.value, '📋')} "
        f"<b>{task.title}</b>\n"
        f"{due_date_str}\n"
    )

    if task.description:
        message += f"\n{task.description}\n"

    return message


# Command handlers
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Welcome to the Task Manager Bot!\n\n"
        "Use /help to see available commands."
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "Available commands:\n"
        "/tasks - Show all your tasks\n"
        "/today - Show tasks due today\n"
        "/week - Show tasks due this week\n"
        "/status - Show tasks by status\n"
        "/priority - Show tasks by priority\n"
        "/category - Show tasks by category\n"
    )

    await message.answer(help_text)


@router.message(Command("tasks"))
async def cmd_tasks(message: Message):
    db = get_db()
    try:
        user = get_user_by_telegram_id(message.from_user.id, db)

        if not user:
            await message.answer(
                "You need to connect your Telegram account with the Task Manager. "
                "Please use the web interface to connect your account."
            )
            return

        tasks = db.query(Task).filter(Task.owner_id == user.id).all()

        if not tasks:
            await message.answer("You don't have any tasks.")
            return

        response = "Your tasks:\n\n"
        for task in tasks[:10]:  # Limit to 10 tasks
            response += format_task_message(task) + "\n"

        if len(tasks) > 10:
            response += f"\nShowing 10 of {len(tasks)} tasks. Use web interface to see all tasks."

        await message.answer(response, parse_mode="HTML")

        # Record metric
        record_telegram_notification("success")
    except Exception as e:
        logger.error(f"Error in cmd_tasks: {e}")
        await message.answer("An error occurred while fetching your tasks.")
        record_telegram_notification("error")
    finally:
        db.close()


@router.message(Command("today"))
async def cmd_today(message: Message):
    db = get_db()
    try:
        user = get_user_by_telegram_id(message.from_user.id, db)

        if not user:
            await message.answer(
                "You need to connect your Telegram account with the Task Manager. "
                "Please use the web interface to connect your account."
            )
            return

        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)

        tasks = (
            db.query(Task)
            .filter(
                Task.owner_id == user.id,
                Task.due_date >= today,
                Task.due_date < tomorrow,
            )
            .all()
        )

        if not tasks:
            await message.answer("You don't have any tasks due today.")
            return

        response = "Tasks due today:\n\n"
        for task in tasks:
            response += format_task_message(task) + "\n"

        await message.answer(response, parse_mode="HTML")

        # Record metric
        record_telegram_notification("success")
    except Exception as e:
        logger.error(f"Error in cmd_today: {e}")
        await message.answer("An error occurred while fetching your tasks.")
        record_telegram_notification("error")
    finally:
        db.close()


@router.message(Command("week"))
async def cmd_week(message: Message):
    db = get_db()
    try:
        user = get_user_by_telegram_id(message.from_user.id, db)

        if not user:
            await message.answer(
                "You need to connect your Telegram account with the Task Manager. "
                "Please use the web interface to connect your account."
            )
            return

        today = datetime.utcnow().date()
        week_later = today + timedelta(days=7)

        tasks = (
            db.query(Task)
            .filter(
                Task.owner_id == user.id,
                Task.due_date >= today,
                Task.due_date < week_later,
            )
            .all()
        )

        if not tasks:
            await message.answer("You don't have any tasks due this week.")
            return

        response = "Tasks due this week:\n\n"
        for task in tasks[:15]:  # Limit to 15 tasks
            response += format_task_message(task) + "\n"

        if len(tasks) > 15:
            response += f"\nShowing 15 of {len(tasks)} tasks. Use web interface to see all tasks."

        await message.answer(response, parse_mode="HTML")

        # Record metric
        record_telegram_notification("success")
    except Exception as e:
        logger.error(f"Error in cmd_week: {e}")
        await message.answer("An error occurred while fetching your tasks.")
        record_telegram_notification("error")
    finally:
        db.close()


@router.message(Command("status"))
async def cmd_status(message: Message):
    db = get_db()
    try:
        user = get_user_by_telegram_id(message.from_user.id, db)

        if not user:
            await message.answer(
                "You need to connect your Telegram account with the Task Manager. "
                "Please use the web interface to connect your account."
            )
            return

        statuses = ["todo", "in_progress", "done", "canceled"]

        response = "Tasks by status:\n\n"
        for status in statuses:
            tasks = (
                db.query(Task)
                .filter(Task.owner_id == user.id, Task.status == status)
                .all()
            )

            if tasks:
                status_emoji = {
                    "todo": "🔲",
                    "in_progress": "🔄",
                    "done": "✅",
                    "canceled": "❌",
                }
                response += f"\n{status_emoji.get(status, '')} <b>{status.upper()}</b>:\n"
                for task in tasks[:5]:  # Limit to 5 tasks per status
                    response += f"- {task.title}\n"

                if len(tasks) > 5:
                    response += f"  ... and {len(tasks) - 5} more\n"

        if response == "Tasks by status:\n\n":
            response = "You don't have any tasks."

        await message.answer(response, parse_mode="HTML")

        # Record metric
        record_telegram_notification("success")
    except Exception as e:
        logger.error(f"Error in cmd_status: {e}")
        await message.answer("An error occurred while fetching your tasks.")
        record_telegram_notification("error")
    finally:
        db.close()


@router.message(Command("priority"))
async def cmd_priority(message: Message):
    db = get_db()
    try:
        user = get_user_by_telegram_id(message.from_user.id, db)

        if not user:
            await message.answer(
                "You need to connect your Telegram account with the Task Manager. "
                "Please use the web interface to connect your account."
            )
            return

        priorities = ["urgent", "high", "medium", "low"]

        response = "Tasks by priority:\n\n"
        for priority in priorities:
            tasks = (
                db.query(Task)
                .filter(Task.owner_id == user.id, Task.priority == priority)
                .all()
            )

            if tasks:
                priority_emoji = {
                    "low": "⬇️",
                    "medium": "➡️",
                    "high": "⬆️",
                    "urgent": "🔥",
                }
                response += f"\n{priority_emoji.get(priority, '')} <b>{priority.upper()}</b>:\n"
                for task in tasks[:5]:  # Limit to 5 tasks per priority
                    response += f"- {task.title}\n"

                if len(tasks) > 5:
                    response += f"  ... and {len(tasks) - 5} more\n"

        if response == "Tasks by priority:\n\n":
            response = "You don't have any tasks."

        await message.answer(response, parse_mode="HTML")

        # Record metric
        record_telegram_notification("success")
    except Exception as e:
        logger.error(f"Error in cmd_priority: {e}")
        await message.answer("An error occurred while fetching your tasks.")
        record_telegram_notification("error")
    finally:
        db.close()


@router.message(Command("category"))
async def cmd_category(message: Message):
    db = get_db()
    try:
        user = get_user_by_telegram_id(message.from_user.id, db)

        if not user:
            await message.answer(
                "You need to connect your Telegram account with the Task Manager. "
                "Please use the web interface to connect your account."
            )
            return

        categories = ["work", "personal", "health", "education", "other"]

        response = "Tasks by category:\n\n"
        for category in categories:
            tasks = (
                db.query(Task)
                .filter(Task.owner_id == user.id, Task.category == category)
                .all()
            )

            if tasks:
                category_emoji = {
                    "personal": "👤",
                    "work": "💼",
                    "health": "🏥",
                    "education": "📚",
                    "other": "📋",
                }
                response += f"\n{category_emoji.get(category, '')} <b>{category.upper()}</b>:\n"
                for task in tasks[:5]:  # Limit to 5 tasks per category
                    response += f"- {task.title}\n"

                if len(tasks) > 5:
                    response += f"  ... and {len(tasks) - 5} more\n"

        if response == "Tasks by category:\n\n":
            response = "You don't have any tasks."

        await message.answer(response, parse_mode="HTML")

        # Record metric
        record_telegram_notification("success")
    except Exception as e:
        logger.error(f"Error in cmd_category: {e}")
        await message.answer("An error occurred while fetching your tasks.")
        record_telegram_notification("error")
    finally:
        db.close()


# Function to check and send reminders
async def check_reminders(bot: Bot):
    while True:
        try:
            db = get_db()
            now = datetime.utcnow()
            five_minutes_ago = now - timedelta(minutes=5)

            # Find reminders that need to be sent
            reminders = (
                db.query(Reminder)
                .filter(
                    Reminder.is_sent == False,
                    Reminder.reminder_time <= now,
                    Reminder.reminder_time >= five_minutes_ago,
                )
                .all()
            )

            for reminder in reminders:
                task = db.query(Task).filter(Task.id == reminder.task_id).first()

                if task:
                    # Get user's Telegram info
                    telegram_user = (
                        db.query(TelegramUser)
                        .filter(TelegramUser.user_id == task.owner_id)
                        .first()
                    )

                    if telegram_user and telegram_user.is_active:
                        # Send reminder
                        message = f"🔔 <b>Reminder</b> 🔔\n\n{format_task_message(task)}"

                        try:
                            await bot.send_message(
                                chat_id=telegram_user.chat_id,
                                text=message,
                                parse_mode="HTML",
                            )

                            # Mark reminder as sent
                            reminder.is_sent = True
                            db.add(reminder)
                            db.commit()

                            # Record metric
                            record_telegram_notification("success")
                        except Exception as e:
                            logger.error(f"Error sending reminder: {e}")
                            record_telegram_notification("error")

            db.close()
        except Exception as e:
            logger.error(f"Error in check_reminders: {e}")

        # Check every minute
        await asyncio.sleep(60)


async def main():
    # Start Prometheus metrics server
    start_http_server(8000)

    # Initialize Bot and Dispatcher
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    # Start reminder checker
    asyncio.create_task(check_reminders(bot))

    # Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())