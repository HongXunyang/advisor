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
        if source.origin == "bundled_example":
            form.addRow("Origin:", self._value_label("Bundled example"))
            if source.citation:
                form.addRow("Citation:", self._value_label(source.citation))
        if source.formula:
            form.addRow("Formula:", self._value_label(source.formula))
        if source.space_group:
            form.addRow("Space group:", self._value_label(str(source.space_group)))
        if source.source_id:
            form.addRow("Source:", self._value_label(source.source_id))
        if source.doi:
            form.addRow("DOI:", self._value_label(source.doi))
        if source.temperature_k is not None:
            form.addRow("Temperature:", self._value_label(f"{source.temperature_k:g} K"))
        if source.pressure_kpa is not None:
            form.addRow("Pressure:", self._value_label(f"{source.pressure_kpa:g} kPa"))

        # Full precision, not `.6g`: Python's `repr()`/`str()` for a float is
        # the shortest decimal string that round-trips back to the exact
        # same value -- REQUIREMENT_2.md's "precise cell values" and
        # Requirement 1's precision guarantee both require this, not a
        # display-rounded approximation (`.6g` on 5.431020511 -> "5.43102",
        # silently losing 5 significant digits -- REVIEW.md finding #8).
        cell = (
            f"a={source.a!r}  b={source.b!r}  c={source.c!r} Å\n"
            f"α={source.alpha!r}°  β={source.beta!r}°  γ={source.gamma!r}°"
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
