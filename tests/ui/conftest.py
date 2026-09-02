"""Shared fixtures for shared-UI (advisor/ui/) tests."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QMessageBox


@pytest.fixture(scope="session")
def qapp():
    """A single headless QApplication instance shared across the test session.

    PyQt5 only allows one QApplication per process, so this must be session
    scoped, and QT_QPA_PLATFORM=offscreen must be set before it is created
    (done above) so tests can run without a display.
    """
    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture
def message_box_calls(monkeypatch):
    """Capture QMessageBox.warning/critical/information calls instead of
    showing a blocking modal dialog, so slot methods can be exercised
    headlessly.

    Each captured call is stored as its raw positional-argument tuple, e.g.
    (parent, title, text), matching how the app code calls
    QMessageBox.warning(self, title, text).
    """

    class Calls:
        def __init__(self):
            self.warnings = []
            self.criticals = []
            self.informations = []

    calls = Calls()

    def fake_warning(*args, **kwargs):
        calls.warnings.append(args)
        return QMessageBox.Ok

    def fake_critical(*args, **kwargs):
        calls.criticals.append(args)
        return QMessageBox.Ok

    def fake_information(*args, **kwargs):
        calls.informations.append(args)
        return QMessageBox.Ok

    monkeypatch.setattr(QMessageBox, "warning", staticmethod(fake_warning))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(fake_critical))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(fake_information))
    return calls
