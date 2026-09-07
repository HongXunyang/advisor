"""On-demand detail view for the currently accepted structure.

Keeps `InitWindow` compact: path, full-precision cell, space group, and
source kind live here instead of a permanent panel (see REQUIREMENT_1's UI
layout acceptance criteria).
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout


class CifDetailsDialog(QDialog):
    """Read-only summary of one `StructureSource`."""

    def __init__(self, source, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Structure Details")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        form.addRow("Name:", self._value_label(source.display_name))
        if source.source_kind == "cif":
            form.addRow("Path:", self._value_label(source.display_path))
            form.addRow("Data block:", self._value_label(source.data_block or "(none)"))
        else:
            form.addRow("Source:", self._value_label("Manual lattice entry"))
        if source.formula:
            form.addRow("Formula:", self._value_label(source.formula))
        if source.space_group:
            form.addRow("Space group:", self._value_label(str(source.space_group)))

        cell = (
            f"a={source.a:.6g}  b={source.b:.6g}  c={source.c:.6g} Å\n"
            f"α={source.alpha:.6g}°  β={source.beta:.6g}°  γ={source.gamma:.6g}°"
        )
        form.addRow("Cell:", self._value_label(cell))

        form.addRow("Geometry:", self._value_label("Available" if source.capabilities.geometry_ok else "Unavailable"))
        form.addRow(
            "Structure factors:",
            self._value_label("Available" if source.capabilities.structure_factor_ok else "Unavailable"),
        )
        if source.capabilities.reasons:
            form.addRow("Notes:", self._value_label("; ".join(source.capabilities.reasons)))

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    @staticmethod
    def _value_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        return label
