"""Deprecated: Use fcp.services.storage instead."""

from fcp.services.storage import (
    StorageClient,
    get_storage,
    get_storage_client,
    is_storage_configured,
    storage_client,
)

__all__ = [
    "StorageClient",
    "get_storage",
    "get_storage_client",
    "is_storage_configured",
    "storage_client",
]
