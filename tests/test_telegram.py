import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Message, User as TelegramUser

from app.telegram.bot import cmd_start, cmd_help, format_task_message
from app.models.task import Task, TaskStatus, TaskPriority, TaskCategory


@pytest.mark.asyncio
async def test_cmd_start():
    # Mock the Message object
    message = AsyncMock(spec=Message)
    message.answer = AsyncMock()

    # Run the command handler
    await cmd_start(message)

    # Assert the response
    message.answer.assert_called_once()
    args, _ = message.answer.call_args
    assert "Welcome to the Task Manager Bot" in args[0]


@pytest.mark.asyncio
async def test_cmd_help():
    # Mock the Message object
    message = AsyncMock(spec=Message)
    message.answer = AsyncMock()

    # Run the command handler
    await cmd_help(message)

    # Assert the response
    message.answer.assert_called_once()
    args, _ = message.answer.call_args
    assert "Available commands" in args[0]


def test_format_task_message():
    # Create a test task
    task = MagicMock(spec=Task)
    task.title = "Test Task"
    task.description = "Test Description"
    task.status = TaskStatus.TODO
    task.priority = TaskPriority.HIGH
    task.category = TaskCategory.WORK
    task.due_date = None

    # Set up the value attributes for the enums
    task.status.value = "todo"
    task.priority.value = "high"
    task.category.value = "work"

    # Format the message
    message = format_task_message(task)

    # Assert the formatted message contains expected elements
    assert "Test Task" in message
    assert "Test Description" in message
    assert "No due date" in message