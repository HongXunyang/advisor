"""Shared fixtures for structure-factor UI tests."""
import pytest
from PyQt5.QtWidgets import QMessageBox


class _Calls:
    def __init__(self):
        self.warnings = []
        self.criticals = []
        self.informations = []


@pytest.fixture
def message_box_calls(monkeypatch):
    """Capture QMessageBox.warning/critical/information instead of showing a
    blocking modal dialog, so slot methods can be exercised headlessly.

    Each captured call is stored as its raw positional-argument tuple, e.g.
    (parent, title, text), matching how the app code calls
    QMessageBox.warning(self, title, text).
    """
    calls = _Calls()

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
