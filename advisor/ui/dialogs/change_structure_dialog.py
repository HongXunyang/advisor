"""The single entry point for managing the current structure from the
working view (or setup) without a separate destructive "Reset Parameters"
button sitting alongside it.

Wraps one `CifDropTarget` (drop/Browse a new CIF, driven through the exact
same `AppController.import_cif()` path as every other entry point) plus a
small, deliberately de-emphasized "Start Over" action that performs the full
destructive reset (`AppController.reset_parameters()`) -- picking a new file
and starting over are two different intents, so they get two different-
weight controls in one dialog rather than two competing top-level buttons.
"""

import os

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialogButtonBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from advisor.ui.components.cif_selector import CifDropTarget


def change_structure_icon() -> QIcon:
    """The one icon for every 'Change Structure…' entry point (toolbar,
    File menu, the per-tab button, and this dialog's own window icon) --
    a single source of truth for the path so it can't drift between call
    sites. Reuses the existing crystal-lattice graphic (`reset.png`) that
    illustrated the old standalone Reset Parameters button; the artwork
    itself (a unit cell) fits "structure" at least as well as "reset."
    """
    import advisor

    icon_path = os.path.join(os.path.dirname(advisor.__file__), "resources", "icons", "reset.png")
    return QIcon(icon_path) if os.path.exists(icon_path) else QIcon()


class ChangeStructureDialog(QDialog):
    """Opens the shared CIF drop target; closes itself on a non-rejected
    result or after Start Over."""

    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.setWindowTitle("Change Structure")
        self.setWindowIcon(change_structure_icon())
        self.setMinimumSize(480, 240)

        layout = QVBoxLayout(self)

        hint = QLabel(
            "Select a new CIF file. The current structure, orientation, and "
            "results stay untouched until a different structure is accepted."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._drop_target = CifDropTarget()
        self._drop_target.cifSelected.connect(self._on_cif_selected)
        self._drop_target.selectionRejected.connect(self._on_rejected)
        layout.addWidget(self._drop_target)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        layout.addStretch(1)

        bottom_row = QHBoxLayout()

        self._start_over_button = QPushButton("Start over")
        self._start_over_button.setToolTip(
            "Clear the current structure, orientation, and results, and "
            "return to a blank setup"
        )
        # Deliberately understated (flat, muted, no border) relative to the
        # dialog's primary action (picking a file) and to Close -- this is
        # the one destructive action in the dialog, not the default choice.
        self._start_over_button.setFlat(True)
        self._start_over_button.setStyleSheet(
            "QPushButton { color: #C62828; border: none; padding: 4px 6px; }"
            "QPushButton:hover { text-decoration: underline; }"
        )
        self._start_over_button.clicked.connect(self._on_start_over)
        bottom_row.addWidget(self._start_over_button)

        bottom_row.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        bottom_row.addWidget(buttons)

        layout.addLayout(bottom_row)

    def _on_cif_selected(self, path: str):
        result = self.app_controller.import_cif(path)
        if result.status == "rejected":
            self._show_status(result.message, error=True)
            return
        self._show_status(result.message, error=False)
        if result.status in ("ready", "ready_geometry_only"):
            self.accept()

    def _on_rejected(self, message: str):
        self._show_status(message, error=True)

    def _on_start_over(self):
        self.app_controller.reset_parameters()
        self.accept()

    def _show_status(self, message: str, error: bool):
        color = "#C62828" if error else "#2d5a3d"
        self._status_label.setStyleSheet(f"color: {color};")
        self._status_label.setText(message)
