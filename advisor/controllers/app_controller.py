"""Top-level application controller."""

import json
import os
from typing import Optional

from PyQt5.QtWidgets import QApplication

from advisor.features import ScatteringGeometryController, StructureFactorController
from advisor.ui.init_window import InitWindow
from advisor.ui.main_window import MainWindow


class AppController:
    """Coordinates application startup and feature wiring."""

    def __init__(self, qt_app: QApplication):
        self.app = qt_app
        self.config = self._load_config()
        self.parameters: Optional[dict] = None

        self.main_window = MainWindow(controller=self)
        self.init_window = InitWindow(controller=self)
        self.main_window.attach_init_view(self.init_window)

        self.features = [
            ScatteringGeometryController(self),
            StructureFactorController(self),
        ]
        for feature in self.features:
            self.main_window.add_feature_tab(
                feature.view, feature.title, feature.icon, feature.description
            )

        self.init_window.initialized.connect(self.apply_parameters)

    def show(self):
        """Show the main window."""
        self.main_window.show()

    def apply_parameters(self, params: dict):
        """Store and propagate global parameters, then show tabs."""
        self.parameters = params
        for feature in self.features:
            feature.set_parameters(params)
        self.main_window.show_tabs()

    def reset_parameters(self):
        """Reset parameters and return to init view."""
        self.parameters = None
        if hasattr(self.init_window, "reset_inputs"):
            self.init_window.reset_inputs()
        self.main_window.show_init()

    def get_parameters(self) -> dict:
        """Return the current global parameters."""
        return self.parameters or {}

    def _load_config(self) -> dict:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, "resources", "config", "app_config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return {
                "app_name": "Ad-VISOR",
                "window_size": {"width": 1200, "height": 800},
            }
