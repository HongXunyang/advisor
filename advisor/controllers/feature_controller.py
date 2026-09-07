"""Base feature controller."""

from typing import Optional
from PyQt5.QtWidgets import QWidget


class FeatureController:
    """Base class for feature controllers."""

    title: str = "Feature"
    description: str = ""
    icon: Optional[str] = None

    def __init__(self, app_controller):
        self.app_controller = app_controller
        self.view: Optional[QWidget] = None

    def set_parameters(self, params: dict):
        """Propagate global parameters to the feature."""
        raise NotImplementedError

    def invalidate_structure(self):
        """Discard this feature's calculators/results/UI state for a structure
        change (replace, remove, or reset).

        Called by ``AppController`` before returning to setup, and again if
        ``apply_parameters`` fails partway through. Must not raise -- a
        feature that can't safely reset should still end up inactive rather
        than throwing out of this call. Default is a no-op for feature
        controllers that own no structure-dependent state.
        """

    def build_view(self) -> QWidget:
        """Create and return the tab widget."""
        raise NotImplementedError

