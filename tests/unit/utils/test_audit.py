"""Tests for structured audit logging."""

import json
import logging
from unittest.mock import patch

import pytest

from fcp.utils.audit import (
    AuditFormatter,
    AuditLogger,
    audit_log,
    audit_logger,
    setup_audit_logging,
)


class TestAuditFormatter:
    """Tests for AuditFormatter."""

    def test_format_basic_record(self):
        """Format basic log record."""
        formatter = AuditFormatter()
        record = logging.LogRecord(
            name="foodlog.audit",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test.event",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["event"] == "test.event"
        assert data["level"] == "INFO"
        assert data["service"] == "fcp-server"
        assert "timestamp" in data

    def test_format_with_extra_fields(self):
        """Format record with extra fields."""
        formatter = AuditFormatter()
        record = logging.LogRecord(
            name="foodlog.audit",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="user.action",
            args=(),
            exc_info=None,
        )
        record.user_id = "user123"
        record.resource_id = "resource456"
        record.action = "delete"

        result = formatter.format(record)
        data = json.loads(result)

        assert data["user_id"] == "user123"
        assert data["resource_id"] == "resource456"
        assert data["action"] == "delete"

    def test_format_with_resource_type_and_ip_address(self):
        """Format record with resource_type and ip_address fields."""
        formatter = AuditFormatter()
        record = logging.LogRecord(
            name="foodlog.audit",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="resource.accessed",
            args=(),
            exc_info=None,
        )
        record.resource_type = "meal"
        record.ip_address = "192.168.1.1"

        result = formatter.format(record)
        data = json.loads(result)

        assert data["resource_type"] == "meal"
        assert data["ip_address"] == "192.168.1.1"

    def test_format_with_metadata(self):
        """Format record with metadata."""
        formatter = AuditFormatter()
        record = logging.LogRecord(
            name="foodlog.audit",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="custom.event",
            args=(),
            exc_info=None,
        )
        record.metadata = {"key": "value", "count": 42}

        result = formatter.format(record)
        data = json.loads(result)

        assert data["metadata"] == {"key": "value", "count": 42}

    def test_format_with_request_id(self):
        """Format record includes request ID from context."""
        formatter = AuditFormatter()
        record = logging.LogRecord(
            name="foodlog.audit",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test.event",
            args=(),
            exc_info=None,
        )

        with patch("fcp.utils.audit.get_request_id", return_value="req-123"):
            result = formatter.format(record)

        data = json.loads(result)
        assert data["request_id"] == "req-123"


class TestAuditLogger:
    """Tests for AuditLogger."""

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return logging.getLogger("test.audit")

    @pytest.fixture
    def audit(self, mock_logger):
        """Create AuditLogger with mock."""
        return AuditLogger(mock_logger)

    def test_info_log(self, audit, mock_logger):
        """Test info level logging."""
        with patch.object(mock_logger, "log") as mock_log:
            audit.info(
                "test.event",
                user_id="user1",
                resource_id="res1",
                action="create",
            )

            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            assert args[0] == logging.INFO
            assert args[1] == "test.event"
            assert kwargs["extra"]["user_id"] == "user1"

    def test_info_log_with_none_values(self, audit, mock_logger):
        """Test info level logging with None values."""
        with patch.object(mock_logger, "log") as mock_log:
            # Call with all None values to test the falsy branches
            audit.info("test.event")

            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            assert args[0] == logging.INFO
            assert kwargs["extra"] == {}  # Empty because all values were None

    def test_warning_log(self, audit, mock_logger):
        """Test warning level logging."""
        with patch.object(mock_logger, "log") as mock_log:
            audit.warning("security.event", user_id="user1")

            args, _ = mock_log.call_args
            assert args[0] == logging.WARNING

    def test_error_log(self, audit, mock_logger):
        """Test error level logging."""
        with patch.object(mock_logger, "log") as mock_log:
            audit.error("critical.event", user_id="user1")

            args, _ = mock_log.call_args
            assert args[0] == logging.ERROR

    def test_log_resource_created(self, audit, mock_logger):
        """Test resource creation logging."""
        with patch.object(mock_logger, "log") as mock_log:
            audit.log_resource_created(
                resource_type="meal",
                resource_id="meal123",
                user_id="user1",
                ip_address="1.2.3.4",
            )

            args, kwargs = mock_log.call_args
            assert args[1] == "meal.created"
            assert kwargs["extra"]["action"] == "create"
            assert kwargs["extra"]["resource_type"] == "meal"

    def test_log_resource_updated(self, audit, mock_logger):
        """Test resource update logging."""
        with patch.object(mock_logger, "log") as mock_log:
            audit.log_resource_updated(
                resource_type="recipe",
                resource_id="recipe456",
                user_id="user2",
            )

            args, kwargs = mock_log.call_args
            assert args[1] == "recipe.updated"
            assert kwargs["extra"]["action"] == "update"

    def test_log_resource_deleted(self, audit, mock_logger):
        """Test resource deletion logging."""
        with patch.object(mock_logger, "log") as mock_log:
            audit.log_resource_deleted(
                resource_type="pantry_item",
                resource_id="item789",
                user_id="user3",
            )

            args, kwargs = mock_log.call_args
            assert args[1] == "pantry_item.deleted"
            assert kwargs["extra"]["action"] == "delete"

    def test_log_access_denied(self, audit, mock_logger):
        """Test access denied logging."""
        with patch.object(mock_logger, "log") as mock_log:
            audit.log_access_denied(
                resource_type="meal",
                resource_id="meal123",
                user_id="attacker",
                ip_address="5.6.7.8",
                reason="unauthorized",
            )

            args, kwargs = mock_log.call_args
            assert args[0] == logging.WARNING
            assert args[1] == "access.denied"
            assert kwargs["extra"]["metadata"]["reason"] == "unauthorized"

    def test_log_authentication_success(self, audit, mock_logger):
        """Test successful authentication logging."""
        with patch.object(mock_logger, "log") as mock_log:
            audit.log_authentication(
                user_id="user1",
                success=True,
                ip_address="1.2.3.4",
                method="firebase",
            )

            args, kwargs = mock_log.call_args
            assert args[0] == logging.INFO
            assert args[1] == "auth.success"

    def test_log_authentication_failure(self, audit, mock_logger):
        """Test failed authentication logging."""
        with patch.object(mock_logger, "log") as mock_log:
            audit.log_authentication(
                user_id="user1",
                success=False,
                ip_address="1.2.3.4",
            )

            args, kwargs = mock_log.call_args
            assert args[0] == logging.WARNING
            assert args[1] == "auth.failure"


class TestSetupAuditLogging:
    """Tests for setup_audit_logging."""

    def test_setup_with_no_file(self):
        """Setup audit logging without file."""
        # Clear existing handlers
        audit_logger.handlers.clear()

        setup_audit_logging()

        assert len(audit_logger.handlers) == 1
        assert isinstance(audit_logger.handlers[0], logging.StreamHandler)

    def test_setup_with_file(self, tmp_path):
        """Setup audit logging with file."""
        log_file = tmp_path / "audit.log"

        # Clear existing handlers
        audit_logger.handlers.clear()

        setup_audit_logging(str(log_file))

        assert len(audit_logger.handlers) == 1
        assert isinstance(audit_logger.handlers[0], logging.FileHandler)


class TestDefaultAuditLog:
    """Tests for default audit_log instance."""

    def test_audit_log_instance_exists(self):
        """Default audit_log instance is available."""
        assert audit_log is not None
        assert isinstance(audit_log, AuditLogger)
