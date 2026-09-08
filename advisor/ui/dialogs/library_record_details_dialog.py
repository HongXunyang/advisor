"""On-demand detail view for one saved `LibraryRecord`.

Separate from `CifDetailsDialog` (which describes the current session's
`StructureSource`): this dialog describes a durable library row -- storage
location, star/note, import/last-used timestamps, and bundled-example
citation -- none of which a bare `StructureSource` carries.
"""

import time

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout


def _format_timestamp(epoch_seconds: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(epoch_seconds))


class LibraryRecordDetailsDialog(QDialog):
    """Read-only summary of one `LibraryRecord`."""

    def __init__(self, record, managed_absolute_path, citation=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Structure Details")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        form.addRow("Name:", self._value_label(record.effective_display_name()))
        form.addRow("Original filename:", self._value_label(record.original_filename))
        form.addRow("Formula:", self._value_label(record.formula or "Not recorded"))
        form.addRow("Space group:", self._value_label(record.space_group or "Not recorded"))

        if all(v is not None for v in (record.cell_a, record.cell_b, record.cell_c,
                                        record.cell_alpha, record.cell_beta, record.cell_gamma)):
            # Full precision (`!r`), not `.6g` -- see CifDetailsDialog's
            # identical fix; this on-demand view is exactly where
            # REQUIREMENT_2.md's "precise cell values" applies (REVIEW.md
            # finding #8). The picker's own compact inline summary is
            # allowed to stay abbreviated; this dialog is not that summary.
            cell = (
                f"a={record.cell_a!r}  b={record.cell_b!r}  c={record.cell_c!r} Å\n"
                f"α={record.cell_alpha!r}°  β={record.cell_beta!r}°  γ={record.cell_gamma!r}°"
            )
        else:
            cell = "Not recorded"
        form.addRow("Cell:", self._value_label(cell))

        form.addRow("Source:", self._value_label(record.source_id or "Not recorded"))
        form.addRow("DOI:", self._value_label(record.doi or "Not recorded"))
        form.addRow(
            "Temperature:",
            self._value_label(f"{record.temperature_k:g} K" if record.temperature_k is not None else "Not recorded"),
        )
        form.addRow(
            "Pressure:",
            self._value_label(f"{record.pressure_kpa:g} kPa" if record.pressure_kpa is not None else "Not recorded"),
        )

        geometry_text = "Not recorded" if record.geometry_ok is None else ("Available" if record.geometry_ok else "Unavailable")
        sf_text = "Not recorded" if record.structure_factor_ok is None else ("Available" if record.structure_factor_ok else "Unavailable")
        form.addRow("Geometry:", self._value_label(geometry_text))
        form.addRow("Structure factors:", self._value_label(sf_text))
        if record.capability_message:
            form.addRow("Notes:", self._value_label(record.capability_message))

        form.addRow("Starred:", self._value_label("Yes" if record.starred else "No"))
        form.addRow("Note:", self._value_label(record.note or "(none)"))
        form.addRow("Imported:", self._value_label(_format_timestamp(record.imported_at)))
        form.addRow("Last used:", self._value_label(_format_timestamp(record.last_used_at)))
        form.addRow(
            "Origin:",
            self._value_label("Bundled example" if record.source_origin == "bundled_example" else "Imported"),
        )
        if citation:
            form.addRow("Citation:", self._value_label(citation))
        if managed_absolute_path:
            form.addRow("Local storage:", self._value_label(managed_absolute_path))

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
