"""Cloud Storage backend for FCP.

This module provides a Cloud Storage backend that matches the Storage interface.
Used in production (Cloud Run) when STORAGE_BACKEND=cloud.
"""

import logging
import mimetypes
import os
import uuid
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

try:
    from google.cloud import storage  # type: ignore[import-untyped]

    STORAGE_AVAILABLE = True
except ImportError:
    storage = None  # type: ignore[assignment]
    STORAGE_AVAILABLE = False


class CloudStorageBackend:
    """Google Cloud Storage backend."""

    def __init__(self, bucket_name: str | None = None, client: Any = None):
        """Initialize GCS client.

        Args:
            bucket_name: Name of the GCS bucket. If None, uses GCS_BUCKET env var.
            client: Optional pre-configured GCS client (for testing).
        """
        self._bucket_name = bucket_name or os.environ.get("GCS_BUCKET")
        self._client = client
        self._bucket = None

    def _ensure_connected(self) -> None:
        """Initialize client and bucket if not yet done."""
        if not STORAGE_AVAILABLE:
            raise RuntimeError("google-cloud-storage not installed. Install with: pip install google-cloud-storage")

        if self._client is None:
            self._client = storage.Client()

        if self._bucket is None:
            if not self._bucket_name:
                raise ValueError("GCS_BUCKET environment variable not set")
            self._bucket = self._client.bucket(self._bucket_name)

    @property
    def is_configured(self) -> bool:
        return bool(self._bucket_name or os.environ.get("GCS_BUCKET"))

    def upload_blob(self, data: bytes, content_type: str, user_id: str, filename: str | None = None) -> str:
        """Upload blob to GCS. Returns the path (blob name)."""
        self._ensure_connected()

        if not filename:
            ext = mimetypes.guess_extension(content_type) or ".bin"
            ext = ext.lstrip(".")
            filename = f"{uuid.uuid4()}.{ext}"
        else:
            filename = os.path.basename(filename)

        date_prefix = datetime.now().strftime("%Y/%m")
        blob_path = f"users/{user_id}/uploads/{date_prefix}/{filename}"

        blob = self._bucket.blob(blob_path)
        blob.upload_from_string(data, content_type=content_type)

        logger.info(f"Uploaded blob to GCS: {blob_path}")
        return blob_path

    def get_public_url(self, path: str) -> str:
        """Return the public GCS URL."""
        return f"https://storage.googleapis.com/{self._bucket_name}/{path}"

    def get_signed_url(self, path: str, expiration_hours: int = 1) -> str:
        """Return a signed GCS URL."""
        self._ensure_connected()
        blob = self._bucket.blob(path)
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=expiration_hours),
            method="GET",
        )
