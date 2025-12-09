#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Base class for all tab implementations."""

from PyQt5.QtWidgets import QWidget, QGridLayout


class TabInterface(QWidget):
    """Base class for feature tabs."""

    def __init__(self, controller=None, main_window=None):
        super().__init__()
        self.controller = controller
        self.main_window = main_window

        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)

        self.init_ui()

    def init_ui(self):
        """Initialize UI components."""
        raise NotImplementedError("Subclasses must implement init_ui()")

    def open_file(self, file_path: str):
        """Handle opening a file."""
        return False

    def save_file(self, file_path: str):
        """Handle saving to a file."""
        return False

    def clear(self):
        """Clear all inputs and results."""
        pass

    def get_state(self) -> dict:
        """Get the current state of the tab for session saving."""
        return {}

    def set_state(self, state: dict):
        """Restore tab state from saved session."""
        return False
