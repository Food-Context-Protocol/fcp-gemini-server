"""Structured audit logging for compliance and security.

Provides a dedicated audit logger that emits structured JSON logs
suitable for compliance requirements (HIPAA, SOC2, GDPR).

Usage:
    from fcp.utils.audit import audit_log

    audit_log.info(
        "meal.created",
        user_id=user_id,
        resource_id=meal_id,
        action="create",
        ip_address=request.client.host,
    )

Log Format:
    {
        "timestamp": "2026-02-01T12:00:00.000Z",
        "event": "meal.created",
        "level": "INFO",
        "user_id": "user123",
        "resource_id": "meal456",
        "action": "create",
        "ip_address": "1.2.3.4",
        "request_id": "abc-123",
        "service": "fcp-server"
    }
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from fcp.utils.logging import get_request_id

# Create dedicated audit logger
audit_logger = logging.getLogger("foodlog.audit")

# Ensure audit logs don't propagate to root logger
audit_logger.propagate = False

# Service identifier
SERVICE_NAME = "fcp-server"


class AuditFormatter(logging.Formatter):
    """JSON formatter for audit logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": record.getMessage(),
            "level": record.levelname,
            "service": SERVICE_NAME,
        }

        if request_id := get_request_id():
            log_data["request_id"] = request_id

        # Add extra fields from record
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "resource_id"):
            log_data["resource_id"] = record.resource_id
        if hasattr(record, "resource_type"):
            log_data["resource_type"] = record.resource_type
        if hasattr(record, "action"):
            log_data["action"] = record.action
        if hasattr(record, "ip_address"):
            log_data["ip_address"] = record.ip_address
        if hasattr(record, "metadata"):
            log_data["metadata"] = record.metadata

        return json.dumps(log_data)


class AuditLogger:
    """Structured audit logger with typed methods.

    Provides type-safe logging methods for common audit events.
    """

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def _log(
        self,
        level: int,
        event: str,
        user_id: str | None = None,
        resource_id: str | None = None,
        resource_type: str | None = None,
        action: str | None = None,
        ip_address: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Internal log method with structured fields."""
        extra: dict[str, Any] = {}
        if user_id:
            extra["user_id"] = user_id
        if resource_id:
            extra["resource_id"] = resource_id
        if resource_type:
            extra["resource_type"] = resource_type
        if action:
            extra["action"] = action
        if ip_address:
            extra["ip_address"] = ip_address
        if metadata:
            extra["metadata"] = metadata

        self._logger.log(level, event, extra=extra)

    def info(
        self,
        event: str,
        user_id: str | None = None,
        resource_id: str | None = None,
        resource_type: str | None = None,
        action: str | None = None,
        ip_address: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log an informational audit event."""
        self._log(
            logging.INFO,
            event,
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            action=action,
            ip_address=ip_address,
            metadata=metadata,
        )

    def warning(
        self,
        event: str,
        user_id: str | None = None,
        resource_id: str | None = None,
        resource_type: str | None = None,
        action: str | None = None,
        ip_address: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a warning audit event."""
        self._log(
            logging.WARNING,
            event,
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            action=action,
            ip_address=ip_address,
            metadata=metadata,
        )

    def error(
        self,
        event: str,
        user_id: str | None = None,
        resource_id: str | None = None,
        resource_type: str | None = None,
        action: str | None = None,
        ip_address: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log an error audit event."""
        self._log(
            logging.ERROR,
            event,
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            action=action,
            ip_address=ip_address,
            metadata=metadata,
        )

    # Convenience methods for common events

    def log_resource_created(
        self,
        resource_type: str,
        resource_id: str,
        user_id: str,
        ip_address: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log resource creation."""
        self.info(
            f"{resource_type}.created",
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            action="create",
            ip_address=ip_address,
            metadata=metadata,
        )

    def log_resource_updated(
        self,
        resource_type: str,
        resource_id: str,
        user_id: str,
        ip_address: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log resource update."""
        self.info(
            f"{resource_type}.updated",
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            action="update",
            ip_address=ip_address,
            metadata=metadata,
        )

    def log_resource_deleted(
        self,
        resource_type: str,
        resource_id: str,
        user_id: str,
        ip_address: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log resource deletion."""
        self.info(
            f"{resource_type}.deleted",
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            action="delete",
            ip_address=ip_address,
            metadata=metadata,
        )

    def log_access_denied(
        self,
        resource_type: str,
        resource_id: str | None,
        user_id: str | None,
        ip_address: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Log access denied event."""
        self.warning(
            "access.denied",
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            action="access_denied",
            ip_address=ip_address,
            metadata={"reason": reason} if reason else None,
        )

    def log_authentication(
        self,
        user_id: str,
        success: bool,
        ip_address: str | None = None,
        method: str = "firebase",
    ) -> None:
        """Log authentication attempt."""
        event = "auth.success" if success else "auth.failure"
        level_method = self.info if success else self.warning
        level_method(
            event,
            user_id=user_id,
            action="authenticate",
            ip_address=ip_address,
            metadata={"method": method},
        )


def setup_audit_logging(log_file: str | None = None) -> None:
    """Configure audit logging.

    Args:
        log_file: Optional file path for audit logs.
                  If None, logs to stderr.
    """
    handler: logging.Handler = logging.FileHandler(log_file) if log_file else logging.StreamHandler()

    handler.setFormatter(AuditFormatter())
    audit_logger.addHandler(handler)
    audit_logger.setLevel(logging.INFO)


# Default audit logger instance
# Note: Call setup_audit_logging() to configure output destination
audit_log = AuditLogger(audit_logger)
