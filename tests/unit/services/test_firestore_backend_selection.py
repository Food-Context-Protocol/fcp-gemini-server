"""Test database backend selection in FirestoreClient."""

import os
from unittest.mock import patch

import pytest

# Import at module level to avoid caching issues
from fcp.services.database import Database


def test_explicit_sqlite_backend():
    """FirestoreClient should use SQLite when explicitly requested."""
    # Import fresh in test scope
    from fcp.services.firestore import FirestoreClient

    client = FirestoreClient(backend="sqlite")

    assert isinstance(client._db, Database)
    assert client._db.__class__.__name__ == "Database"


def test_explicit_firestore_backend():
    """FirestoreClient should use Firestore backend when explicitly requested."""
    from fcp.services.firestore import FirestoreClient

    try:
        client = FirestoreClient(backend="firestore")

        # If google-cloud-firestore is installed, should use FirestoreBackend
        from fcp.services.firestore_backend import FirestoreBackend

        assert isinstance(client._db, FirestoreBackend)
    except (ImportError, RuntimeError):
        # google-cloud-firestore not installed or Firestore not configured
        pytest.skip("google-cloud-firestore not installed (optional dependency)")


def test_health_status_reports_backend():
    """Health check should report which backend is configured."""
    with patch.dict(os.environ, {"DATABASE_BACKEND": "sqlite"}):
        from fcp.services.firestore import get_firestore_status

        status = get_firestore_status()
        assert status["mode"] == "sqlite"
        assert status["available"] is True

    with patch.dict(os.environ, {"DATABASE_BACKEND": "firestore"}):
        from fcp.services.firestore import get_firestore_status

        status = get_firestore_status()
        assert status["mode"] == "firestore"
        assert status["available"] is True
