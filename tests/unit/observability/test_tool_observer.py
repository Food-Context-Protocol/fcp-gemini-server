"""Coverage tests for tool observer."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from fcp.auth.permissions import AuthenticatedUser, UserRole
from fcp.observability.tool_observer import ToolExecutionContext, observe_tool_execution


def test_observe_tool_execution_records():
    user = AuthenticatedUser(user_id="u1", role=UserRole.AUTHENTICATED)
    with patch("fcp.observability.tool_observer.record_tool_call") as record_call:
        with patch("fcp.observability.tool_observer.should_record_tool", return_value=True):
            with patch("fcp.observability.tool_observer.save_recording") as save_recording:
                observe_tool_execution(
                    tool_name="get_recent_meals",
                    arguments={"limit": 1},
                    user=user,
                    duration_seconds=0.5,
                    status="success",
                    result={"meals": []},
                )
                record_call.assert_called_once()
                save_recording.assert_called_once()


def test_observe_tool_execution_no_recording():
    user = AuthenticatedUser(user_id="u1", role=UserRole.AUTHENTICATED)
    with patch("fcp.observability.tool_observer.record_tool_call") as record_call:
        with patch("fcp.observability.tool_observer.should_record_tool", return_value=False):
            with patch("fcp.observability.tool_observer.save_recording") as save_recording:
                observe_tool_execution(
                    tool_name="get_recent_meals",
                    arguments={"limit": 1},
                    user=user,
                    duration_seconds=0.5,
                    status="success",
                    result=[1, 2, 3],
                )
                record_call.assert_called_once()
                save_recording.assert_not_called()


@pytest.mark.asyncio
async def test_tool_execution_context_success():
    user = AuthenticatedUser(user_id="u1", role=UserRole.DEMO)
    with patch("fcp.observability.tool_observer.record_tool_call") as record_call:
        with patch("fcp.observability.tool_observer.should_record_tool", return_value=False):
            ctx = ToolExecutionContext("tool", {"a": 1}, user)
            async with ctx:
                ctx.set_result([1, 2, 3])
            record_call.assert_called_once()


@pytest.mark.asyncio
async def test_tool_execution_context_error():
    user = AuthenticatedUser(user_id="u1", role=UserRole.DEMO)
    with patch("fcp.observability.tool_observer.record_tool_call") as record_call:
        with patch("fcp.observability.tool_observer.should_record_tool", return_value=True):
            with patch("fcp.observability.tool_observer.save_recording") as save_recording:
                ctx = ToolExecutionContext("tool", {"a": 1}, user)
                with pytest.raises(ValueError):
                    async with ctx:
                        raise ValueError("boom")
                record_call.assert_called_once()
                save_recording.assert_called_once()


@pytest.mark.asyncio
async def test_tool_execution_context_with_recording():
    user = AuthenticatedUser(user_id="u1", role=UserRole.AUTHENTICATED)
    with patch("fcp.observability.tool_observer.record_tool_call"):
        with patch("fcp.observability.tool_observer.should_record_tool", return_value=True):
            with patch("fcp.observability.tool_observer.save_recording") as save_recording:
                ctx = ToolExecutionContext("tool", {"a": 1}, user)
                async with ctx:
                    ctx.set_result({"ok": True})
                save_recording.assert_called_once()


def test_result_summary_and_error_truncation():
    """Test _get_result_summary and set_error truncation."""
    user = AuthenticatedUser(user_id="u1", role=UserRole.DEMO)
    ctx = ToolExecutionContext("tool", {"a": 1}, user)
    ctx.set_result({"a": 1})
    summary = ctx._get_result_summary()
    assert summary is not None
    assert "dict keys" in summary
    ctx.set_result([1, 2])
    summary = ctx._get_result_summary()
    assert summary is not None
    assert "list len" in summary
    ctx.set_result("ok")
    summary = ctx._get_result_summary()
    assert summary is not None
    assert "type:" in summary
    ctx.set_result(None)
    assert ctx._get_result_summary() is None
    ctx.set_error("x" * 1000)
    assert len(ctx._error_message) == 500
