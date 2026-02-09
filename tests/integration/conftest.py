"""Integration test fixtures.

This module provides fixtures for integration tests that require
external services (Gemini API).

Prerequisites:
    - .env file with GEMINI_API_KEY

Authentication approach:
    Integration tests use FastAPI dependency overrides to bypass auth.
"""

import importlib
import logging
import os
import socket
import time
from collections.abc import Generator

import httpx
import pytest

if os.getenv("RUN_INTEGRATION") == "1":
    gemini_module = importlib.import_module("fcp.services.gemini")
    from fcp import services as fcp_services  # noqa: E402
    from tests.fakes.fake_gemini import FakeGeminiClient  # noqa: E402

    fake_gemini_client = FakeGeminiClient(
        grounding_sources=[{"title": "Test Source", "url": "https://example.com"}],
        function_calls=[{"name": "noop", "args": {}}],
    )

    fake_gemini_client.GeminiClient = lambda *args, **kwargs: fake_gemini_client
    fake_gemini_client.get_gemini_client = lambda: fake_gemini_client
    fake_gemini_client.get_gemini = lambda: fake_gemini_client

    # Ensure the exported proxy always delegates to the fake client.
    gemini_module.set_gemini_client(fake_gemini_client)
    fcp_services.gemini = gemini_module.gemini
else:
    gemini_module = None
    fake_gemini_client = None

logger = logging.getLogger("tests.integration")

# Configuration
EMULATOR_HOST = "localhost"
FIRESTORE_PORT = 8081
AUTH_PORT = 9099
TEST_PROJECT_ID = "demo-no-project"
TEST_USER_ID = "integration-test-user"


def _check_emulator_running(port: int) -> bool:
    """Check if an emulator is running on the specified port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(1)
        result = sock.connect_ex((EMULATOR_HOST, port))
        return result == 0
    finally:
        sock.close()


def pytest_configure(config):
    """Pytest hook that runs before test collection."""
    # Only adjust environment when integration tests are explicitly enabled.
    if os.getenv("RUN_INTEGRATION") != "1":
        return

    # Load .env for GEMINI_API_KEY etc
    from dotenv import load_dotenv

    load_dotenv()

    # If unit-test defaults are set, clear them for integration runs.
    if os.environ.get("GEMINI_API_KEY") == "test-api-key":
        os.environ.pop("GEMINI_API_KEY", None)


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless explicitly enabled."""
    if os.getenv("RUN_INTEGRATION") == "1":
        return
    skip = pytest.mark.skip(reason="Set RUN_INTEGRATION=1 to run integration tests")
    for item in items:
        if "/tests/integration/" in str(item.fspath):
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def skip_integration_if_missing_deps():
    """Skip tests early when required credentials are absent."""
    if os.getenv("RUN_INTEGRATION") != "1":
        return

    missing = []
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        missing.append("GEMINI_API_KEY")

    if missing:
        msg = f"Skipping integration test because {', '.join(missing)} {'is' if len(missing) == 1 else 'are'} not configured"
        logger.warning(msg)
        pytest.skip(msg)

    os.environ["GOOGLE_CLOUD_PROJECT"] = TEST_PROJECT_ID
    os.environ["DEMO_MODE"] = "false"


@pytest.fixture(autouse=True)
def fake_gemini():
    """Yield the fake Gemini client for tests."""
    if gemini_module is None or fake_gemini_client is None:
        yield None
        return

    gemini_module.set_gemini_client(fake_gemini_client)
    yield fake_gemini_client


def _wait_for_emulator(port: int, timeout: int = 30) -> bool:
    """Wait for emulator to be ready."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if _check_emulator_running(port):
            return True
        time.sleep(0.5)
    return False


@pytest.fixture(scope="session")
def firebase_emulator_env() -> Generator[dict[str, str], None, None]:
    """Set up environment for Firebase emulator.

    This fixture verifies the emulator is running and returns the env vars.
    Environment variables are already set at module load time.
    """
    # Check if emulators are running
    if not _check_emulator_running(FIRESTORE_PORT):
        pytest.skip(
            f"Firestore emulator not running on port {FIRESTORE_PORT}. "
            "Start with: firebase emulators:start --only firestore,auth"
        )

    if not _check_emulator_running(AUTH_PORT):
        pytest.skip(
            f"Auth emulator not running on port {AUTH_PORT}. Start with: firebase emulators:start --only firestore,auth"
        )

    yield {
        "FIRESTORE_EMULATOR_HOST": f"{EMULATOR_HOST}:{FIRESTORE_PORT}",
        "FIREBASE_AUTH_EMULATOR_HOST": f"{EMULATOR_HOST}:{AUTH_PORT}",
        "GCLOUD_PROJECT": TEST_PROJECT_ID,
        "GOOGLE_CLOUD_PROJECT": TEST_PROJECT_ID,
    }


@pytest.fixture
def clear_firestore(firebase_emulator_env: dict[str, str]) -> Generator[None, None, None]:
    """Clear all Firestore data between tests.

    This fixture clears the Firestore emulator database before each test
    to ensure test isolation.
    """
    try:
        # Clear Firestore emulator data
        clear_url = (
            f"http://{EMULATOR_HOST}:{FIRESTORE_PORT}"
            f"/emulator/v1/projects/{TEST_PROJECT_ID}/databases/(default)/documents"
        )
        response = httpx.delete(clear_url, timeout=5.0)
        if response.status_code not in (200, 404):
            pytest.skip(f"Failed to clear Firestore: {response.status_code}")
    except Exception as e:
        pytest.skip(f"Failed to clear Firestore: {e}")

    yield


@pytest.fixture
def test_user_id() -> str:
    """Return a consistent test user ID for integration tests."""
    return TEST_USER_ID


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return authorization headers for API requests.

    Note: The actual token doesn't matter because we override the auth
    dependencies in integration tests. This header just signals that
    the request should be treated as authenticated.
    """
    return {"Authorization": "Bearer integration-test-token"}


@pytest.fixture
async def integration_client(firebase_emulator_env: dict[str, str], clear_firestore: None):
    """Create an async test client for integration tests.

    This fixture creates a test client with authentication bypassed via
    dependency overrides. This allows testing API routes without relying
    on Firebase SDK's emulator integration.
    """
    from httpx import ASGITransport, AsyncClient

    # Now import the app
    from fcp.api import app

    # Import auth types for dependency override
    from fcp.auth.permissions import AuthenticatedUser, UserRole

    # Create a mock authenticated user for tests
    async def mock_get_current_user():
        """Return a mock authenticated user for integration tests."""
        return AuthenticatedUser(user_id=TEST_USER_ID, role=UserRole.AUTHENTICATED)

    async def mock_require_write_access():
        """Return a mock authenticated user with write access."""
        return AuthenticatedUser(user_id=TEST_USER_ID, role=UserRole.AUTHENTICATED)

    # Import the actual dependencies to override
    from fcp.auth.local import get_current_user
    from fcp.auth.permissions import require_write_access

    # Override auth dependencies for integration tests
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[require_write_access] = mock_require_write_access

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            timeout=35.0,  # Slightly above Gemini's 30s timeout
        ) as client:
            yield client
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()
