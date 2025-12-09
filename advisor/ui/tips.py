"""Tooltip helper utilities."""

import json
import os


def _tips_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "resources", "config", "tips.json")


class Tips:
    """Load tooltip text from resources/config/tips.json."""

    def __init__(self):
        self.tips = {}
        try:
            with open(_tips_path(), "r", encoding="utf-8") as handle:
                self.tips = json.load(handle)
        except FileNotFoundError:
            self.tips = {}

    def tip(self, key):
        return self.tips.get(key, "")


def set_tip(widget, tip):
    """Set the tooltip and status tip for a widget."""
    widget.setToolTip(tip)
    widget.setStatusTip(tip)
