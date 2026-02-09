"""Tests for background_tasks utility module."""

import asyncio

import pytest

from fcp.utils.background_tasks import (
    _background_tasks,
    cancel_all_tasks,
    create_tracked_task,
    get_pending_task_count,
    get_pending_tasks,
)


@pytest.fixture(autouse=True)
def clear_tasks():
    """Clear the task registry before and after each test."""
    _background_tasks.clear()
    yield
    _background_tasks.clear()


class TestCreateTrackedTask:
    """Tests for create_tracked_task function."""

    @pytest.mark.asyncio
    async def test_creates_and_tracks_task(self):
        """Test that create_tracked_task creates and registers a task."""

        async def dummy_coro():
            return "done"

        task = create_tracked_task(dummy_coro(), name="test_task")

        assert task is not None
        assert task in _background_tasks
        assert task.get_name() == "test_task"

        # Wait for task to complete
        await task
        # Task should be removed after completion
        assert task not in _background_tasks

    @pytest.mark.asyncio
    async def test_task_removed_on_success(self):
        """Test that task is removed from registry on successful completion."""

        async def quick_task():
            return 42

        task = create_tracked_task(quick_task(), name="quick")
        assert get_pending_task_count() == 1

        result = await task
        assert result == 42

        assert get_pending_task_count() == 0

    @pytest.mark.asyncio
    async def test_task_removed_on_failure(self):
        """Test that task is removed from registry on failure."""

        async def failing_task():
            raise ValueError("Intentional failure")

        task = create_tracked_task(failing_task(), name="failing")
        assert get_pending_task_count() == 1

        with pytest.raises(ValueError, match="Intentional failure"):
            await task

        assert get_pending_task_count() == 0


class TestGetPendingTasks:
    """Tests for get_pending_tasks function."""

    @pytest.mark.asyncio
    async def test_returns_copy(self):
        """Test that get_pending_tasks returns a copy."""

        async def long_running():
            await asyncio.Event().wait()

        task = create_tracked_task(long_running(), name="long")

        tasks = get_pending_tasks()
        assert task in tasks

        # Modifying returned set shouldn't affect internal registry
        tasks.clear()
        assert get_pending_task_count() == 1

        # Cleanup
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


class TestGetPendingTaskCount:
    """Tests for get_pending_task_count function."""

    @pytest.mark.asyncio
    async def test_returns_count(self):
        """Test that get_pending_task_count returns correct count."""
        assert get_pending_task_count() == 0

        async def wait_forever():
            await asyncio.Event().wait()

        task1 = create_tracked_task(wait_forever(), name="task1")
        assert get_pending_task_count() == 1

        task2 = create_tracked_task(wait_forever(), name="task2")
        assert get_pending_task_count() == 2

        # Cleanup
        task1.cancel()
        task2.cancel()
        try:
            await task1
        except asyncio.CancelledError:
            pass
        try:
            await task2
        except asyncio.CancelledError:
            pass


class TestCancelAllTasks:
    """Tests for cancel_all_tasks function."""

    @pytest.mark.asyncio
    async def test_cancels_all_tasks(self):
        """Test that cancel_all_tasks cancels all pending tasks."""

        async def long_running():
            await asyncio.Event().wait()

        create_tracked_task(long_running(), name="task1")
        create_tracked_task(long_running(), name="task2")
        create_tracked_task(long_running(), name="task3")

        assert get_pending_task_count() == 3

        await cancel_all_tasks()

        assert get_pending_task_count() == 0

    @pytest.mark.asyncio
    async def test_cancel_empty_registry(self):
        """Test that cancel_all_tasks works with no tasks."""
        assert get_pending_task_count() == 0
        await cancel_all_tasks()  # Should not raise
        assert get_pending_task_count() == 0
