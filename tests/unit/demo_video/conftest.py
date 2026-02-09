"""Conftest for demo-video module tests.

Adds the demo-video directory to sys.path so we can import its modules.
"""

import sys
from pathlib import Path

# Add demo-video/ to import path
DEMO_VIDEO_DIR = str(Path(__file__).resolve().parents[3] / "demo-video")
if DEMO_VIDEO_DIR not in sys.path:
    sys.path.insert(0, DEMO_VIDEO_DIR)


def pytest_configure(config):
    """Suppress unawaited coroutine warnings from global conftest's autouse async fixtures.

    These leak between test modules when pytest collects unraisable exceptions;
    they're not related to demo-video tests.
    """
    config.addinivalue_line(
        "filterwarnings",
        "ignore::pytest.PytestUnraisableExceptionWarning",
    )
