"""Tests for unified storage client."""

from unittest.mock import MagicMock, patch

from fcp.services.storage import StorageClient, _get_legacy_client, _StorageClientProxy, get_storage_client


class TestStorageClient:
    def test_init_with_injected_client(self):
        """Lines 82-85: client injection path."""
        mock_backend = MagicMock()
        client = StorageClient(client=mock_backend)
        assert client._backend is mock_backend

    def test_init_cloud_backend(self):
        """Lines 89-93: cloud backend initialization."""
        mock_cloud_cls = MagicMock()
        mock_module = MagicMock()
        mock_module.CloudStorageBackend = mock_cloud_cls
        with patch.dict("sys.modules", {"fcp.services.cloud_storage_backend": mock_module}):
            client = StorageClient(backend="cloud")
            mock_cloud_cls.assert_called_once()
            assert client._backend is mock_cloud_cls.return_value


class TestLegacyClient:
    def test_get_legacy_client_creates_singleton(self):
        """Lines 136-139: normal path where singleton is created."""
        import fcp.services.storage as mod

        original = mod._storage_client
        mod._storage_client = None
        try:
            get_storage_client.cache_clear()
            result = _get_legacy_client()
            assert result is not None
            assert mod._storage_client is not None
        finally:
            mod._storage_client = original
            get_storage_client.cache_clear()

    def test_get_legacy_client_double_check_already_set(self):
        """Lines 138->140: double-checked locking inner branch (already set by another thread)."""
        import fcp.services.storage as mod

        original = mod._storage_client
        original_lock = mod._storage_lock
        sentinel = StorageClient()

        # Custom lock whose __enter__ simulates another thread setting the singleton
        class SimulateRaceLock:
            def __enter__(self):
                mod._storage_client = sentinel
                return self

            def __exit__(self, *args):
                pass

        mod._storage_client = None
        mod._storage_lock = SimulateRaceLock()  # type: ignore[assignment]
        try:
            result = _get_legacy_client()
            # Should return the value set by the "other thread"
            assert result is sentinel
        finally:
            mod._storage_client = original
            mod._storage_lock = original_lock
            get_storage_client.cache_clear()


class TestStorageClientProxy:
    def test_repr(self):
        """Line 151: __repr__."""
        proxy = _StorageClientProxy()
        r = repr(proxy)
        assert "StorageClientProxy" in r
        assert "initialized=" in r
