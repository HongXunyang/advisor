"""Shared fixtures for shared-UI (advisor/ui/) tests."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """A single headless QApplication instance shared across the test session.

    PyQt5 only allows one QApplication per process, so this must be session
    scoped, and QT_QPA_PLATFORM=offscreen must be set before it is created
    (done above) so tests can run without a display.
    """
    app = QApplication.instance() or QApplication([])
    return app
