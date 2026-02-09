"""Unified storage client with pluggable backends.

This module provides a unified interface that works with either:
- Local Filesystem (default, for local development)
- Google Cloud Storage (for production on Cloud Run)

Backend selection is controlled by STORAGE_BACKEND environment variable:
- STORAGE_BACKEND=local (default) - uses local filesystem
- STORAGE_BACKEND=cloud - uses Google Cloud Storage
"""

import logging
import os
import threading
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)


class LocalStorageBackend:
    """Local filesystem storage client."""

    def __init__(self):
        import mimetypes
        import uuid
        from datetime import datetime
        from pathlib import Path

        self._mimetypes = mimetypes
        self._uuid = uuid
        self._datetime = datetime
        self._Path = Path
        self._data_dir = Path(os.environ.get("FCP_DATA_DIR", "data"))
        self._uploads_dir = self._data_dir / "uploads"

    @property
    def is_configured(self) -> bool:
        return True

    def upload_blob(self, data: bytes, content_type: str, user_id: str, filename: str | None = None) -> str:
        """Save file to local filesystem. Returns the relative path."""
        if not filename:
            ext = self._mimetypes.guess_extension(content_type) or ".bin"
            ext = ext.lstrip(".")
            filename = f"{self._uuid.uuid4()}.{ext}"
        else:
            if filename in (".", "..") or ".." in filename:
                raise ValueError("Invalid filename")
            filename = os.path.basename(filename)
            if not filename or filename in (".", ".."):
                raise ValueError("Invalid filename")

        date_prefix = self._datetime.now().strftime("%Y/%m")
        rel_path = f"users/{user_id}/uploads/{date_prefix}/{filename}"
        full_path = self._uploads_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        return str(rel_path)

    def get_public_url(self, path: str) -> str:
        """Return a file:// URL for local files."""
        full_path = self._uploads_dir / path
        return f"file://{full_path.resolve()}"

    def get_signed_url(self, path: str, expiration_hours: int = 1) -> str:
        """For local storage, just return the public URL."""
        return self.get_public_url(path)


class StorageClient:
    """Unified storage client with pluggable backend (Local or Cloud)."""

    def __init__(self, backend: str | None = None, client: Any = None):
        """Initialize client with specified backend or inject an instance.

        Args:
            backend: "local" or "cloud". If None, reads from STORAGE_BACKEND env var.
                     Defaults to "local" if not specified.
            client: Optional backend instance for dependency injection (testing).
        """
        if client is not None:
            self._backend = client
            logger.info("Using injected storage backend instance")
            return

        backend_type = backend or os.environ.get("STORAGE_BACKEND", "local")

        if backend_type == "cloud":
            from fcp.services.cloud_storage_backend import CloudStorageBackend

            self._backend = CloudStorageBackend()
            logger.info("Using Google Cloud Storage backend")
        else:
            self._backend = LocalStorageBackend()
            logger.info("Using Local Filesystem backend")

    @property
    def is_configured(self) -> bool:
        return self._backend.is_configured

    def upload_blob(self, data: bytes, content_type: str, user_id: str, filename: str | None = None) -> str:
        return self._backend.upload_blob(data, content_type, user_id, filename)

    def get_public_url(self, path: str) -> str:
        return self._backend.get_public_url(path)

    def get_signed_url(self, path: str, expiration_hours: int = 1) -> str:
        return self._backend.get_signed_url(path, expiration_hours)


@lru_cache(maxsize=1)
def get_storage_client() -> StorageClient:
    """Get or create the StorageClient singleton."""
    return StorageClient()


def get_storage() -> StorageClient:
    """FastAPI dependency for storage client."""
    return get_storage_client()


def is_storage_configured() -> bool:
    """Check if storage is configured."""
    return get_storage_client().is_configured


# Legacy module-level singleton
_storage_client: StorageClient | None = None
_storage_lock = threading.Lock()


def _get_legacy_client() -> StorageClient:
    """Get legacy singleton."""
    global _storage_client  # noqa: PLW0603
    if _storage_client is None:
        with _storage_lock:
            if _storage_client is None:
                _storage_client = get_storage_client()
    assert _storage_client is not None
    return _storage_client


class _StorageClientProxy:
    """Lazy proxy for StorageClient."""

    def __getattr__(self, name: str) -> Any:
        return getattr(_get_legacy_client(), name)

    def __repr__(self) -> str:
        return f"<StorageClientProxy initialized={_storage_client is not None}>"


# Backwards-compatible lazy proxy to the singleton client
storage_client = _StorageClientProxy()
