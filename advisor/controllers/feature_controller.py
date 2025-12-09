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

    def build_view(self) -> QWidget:
        """Create and return the tab widget."""
        raise NotImplementedError

