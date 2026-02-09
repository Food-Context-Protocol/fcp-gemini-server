"""Tests for fcp.services.local_storage module."""

import re
from unittest.mock import patch

import pytest

from fcp.services.local_storage import (
    StorageClient,
    get_storage,
    get_storage_client,
    is_storage_configured,
    storage_client,
)
from fcp.services.storage import _StorageClientProxy


def test_is_storage_configured_returns_true():
    assert is_storage_configured() is True


def test_storage_client_is_configured_property():
    client = StorageClient()
    assert client.is_configured is True


class TestUploadBlob:
    """Tests for StorageClient.upload_blob()."""

    def test_upload_no_filename_auto_generates(self, tmp_path):
        with patch.dict("os.environ", {"FCP_DATA_DIR": str(tmp_path)}):
            client = StorageClient()
            rel_path = client.upload_blob(b"hello", "text/plain", "user1")
            assert rel_path.startswith("users/user1/uploads/")
            assert rel_path.endswith(".txt")
            assert (tmp_path / "uploads" / rel_path).exists()
            assert (tmp_path / "uploads" / rel_path).read_bytes() == b"hello"

    def test_upload_no_filename_unknown_content_type(self, tmp_path):
        with patch.dict("os.environ", {"FCP_DATA_DIR": str(tmp_path)}):
            client = StorageClient()
            rel_path = client.upload_blob(b"data", "application/x-unknown-type-zzzz", "user1")
            assert rel_path.endswith(".bin")
            assert (tmp_path / "uploads" / rel_path).exists()

    def test_upload_with_valid_filename(self, tmp_path):
        with patch.dict("os.environ", {"FCP_DATA_DIR": str(tmp_path)}):
            client = StorageClient()
            rel_path = client.upload_blob(b"image data", "image/png", "user1", filename="photo.png")
            assert rel_path.endswith("photo.png")
            assert (tmp_path / "uploads" / rel_path).exists()
            assert (tmp_path / "uploads" / rel_path).read_bytes() == b"image data"

    def test_upload_with_dotdot_filename_raises(self, tmp_path):
        with patch.dict("os.environ", {"FCP_DATA_DIR": str(tmp_path)}):
            client = StorageClient()
            with pytest.raises(ValueError, match="Invalid filename"):
                client.upload_blob(b"x", "text/plain", "user1", filename="..")

    def test_upload_with_path_traversal_filename_raises(self, tmp_path):
        with patch.dict("os.environ", {"FCP_DATA_DIR": str(tmp_path)}):
            client = StorageClient()
            with pytest.raises(ValueError, match="Invalid filename"):
                client.upload_blob(b"x", "text/plain", "user1", filename="../etc/passwd")

    def test_upload_with_dot_filename_raises(self, tmp_path):
        with patch.dict("os.environ", {"FCP_DATA_DIR": str(tmp_path)}):
            client = StorageClient()
            with pytest.raises(ValueError, match="Invalid filename"):
                client.upload_blob(b"x", "text/plain", "user1", filename=".")

    def test_upload_with_trailing_slash_filename_raises(self, tmp_path):
        """Filename whose basename is empty after os.path.basename (e.g. 'foo/')."""
        with patch.dict("os.environ", {"FCP_DATA_DIR": str(tmp_path)}):
            client = StorageClient()
            with pytest.raises(ValueError, match="Invalid filename"):
                client.upload_blob(b"x", "text/plain", "user1", filename="foo/")

    def test_upload_date_prefix_format(self, tmp_path):
        with patch.dict("os.environ", {"FCP_DATA_DIR": str(tmp_path)}):
            client = StorageClient()
            rel_path = client.upload_blob(b"test", "text/plain", "u1", filename="f.txt")
            # Verify the path contains a YYYY/MM date prefix
            assert re.search(r"uploads/\d{4}/\d{2}/f\.txt$", rel_path)


class TestGetPublicUrl:
    """Tests for StorageClient.get_public_url()."""

    def test_returns_file_url(self, tmp_path):
        with patch.dict("os.environ", {"FCP_DATA_DIR": str(tmp_path)}):
            client = StorageClient()
            url = client.get_public_url("users/u1/uploads/2026/02/photo.png")
            assert url.startswith("file://")
            assert "users/u1/uploads/2026/02/photo.png" in url


class TestGetSignedUrl:
    """Tests for StorageClient.get_signed_url()."""

    def test_returns_same_as_public_url(self, tmp_path):
        with patch.dict("os.environ", {"FCP_DATA_DIR": str(tmp_path)}):
            client = StorageClient()
            path = "users/u1/uploads/2026/02/photo.png"
            assert client.get_signed_url(path) == client.get_public_url(path)
            assert client.get_signed_url(path, expiration_hours=24) == client.get_public_url(path)


class TestGetStorageClient:
    """Tests for get_storage_client() singleton."""

    def test_returns_storage_client_instance(self):
        get_storage_client.cache_clear()
        client = get_storage_client()
        assert isinstance(client, StorageClient)

    def test_returns_same_instance_on_second_call(self):
        get_storage_client.cache_clear()
        client1 = get_storage_client()
        client2 = get_storage_client()
        assert client1 is client2


class TestGetStorage:
    """Tests for get_storage() convenience function."""

    def test_returns_storage_client(self):
        result = get_storage()
        assert isinstance(result, StorageClient)


class TestModuleLevelStorageClient:
    """Tests for module-level storage_client variable."""

    def test_storage_client_is_proxy_instance(self):
        assert isinstance(storage_client, _StorageClientProxy)
