"""Background task management utilities.

This module provides a centralized way to create and track background asyncio tasks.
Tasks are registered to prevent garbage collection and logged when they complete.
"""

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger(__name__)

# Global registry for background tasks
_background_tasks: set[asyncio.Task] = set()


def create_tracked_task(coro: Coroutine[Any, Any, Any], name: str | None = None) -> asyncio.Task:
    """
    Create and track a background task.

    Ensures the task is not garbage collected and logs when it completes.

    Args:
        coro: The coroutine to run as a background task
        name: Optional name for the task (for logging/debugging)

    Returns:
        The created asyncio.Task
    """
    task = asyncio.create_task(coro, name=name)
    _background_tasks.add(task)

    def on_task_done(t: asyncio.Task) -> None:
        _background_tasks.discard(t)
        if t.exception() is not None:
            logger.error(f"Background task {t.get_name()} failed: {t.exception()}")

    task.add_done_callback(on_task_done)
    return task


def get_pending_tasks() -> set[asyncio.Task]:
    """
    Get the set of pending background tasks.

    Returns:
        Set of currently tracked tasks
    """
    return _background_tasks.copy()


def get_pending_task_count() -> int:
    """
    Get the count of pending background tasks.

    Returns:
        Number of currently tracked tasks
    """
    return len(_background_tasks)


async def cancel_all_tasks() -> None:
    """
    Cancel all tracked background tasks and wait for them to complete.

    This should be called during application shutdown.
    """
    if _background_tasks:
        logger.info(f"Cancelling {len(_background_tasks)} background tasks...")
        for task in _background_tasks:
            task.cancel()
        # Wait for tasks to complete cancellation
        await asyncio.gather(*_background_tasks, return_exceptions=True)
        _background_tasks.clear()
