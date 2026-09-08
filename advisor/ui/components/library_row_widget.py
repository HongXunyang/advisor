"""One row's presentation inside `LibraryPickerDialog`'s list.

Purely presentational -- reads a `LibraryRecord`, holds no library logic of
its own. Kept compact: name/formula on one line, one distinguishing
condition/capability line below, "Not recorded" rather than a fabricated
default for missing metadata.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

# A picker row must never force horizontal scrolling regardless of how long
# a user-editable display name or note-derived text gets (REVIEW.md finding
# #7: an unclamped QLabel sizeHint let a 500-character name balloon one row
# to ~4870px in a 560px-wide dialog). Eliding the *text itself* at a fixed
# budget -- rather than only capping the widget's rendered width -- is what
# actually keeps the label's own sizeHint (and therefore the QListWidgetItem
# sizeHint the view lays out against) bounded; a full copy remains reachable
# via the tooltip.
_MAX_NAME_WIDTH_PX = 320
_MAX_FORMULA_WIDTH_PX = 120


def _elided(label: QLabel, text: str, max_width_px: int) -> None:
    metrics = QFontMetrics(label.font())
    label.setText(metrics.elidedText(text, Qt.ElideMiddle, max_width_px))
    label.setToolTip(text)


def _condition_text(record) -> str:
    parts = []
    if record.temperature_k is not None:
        parts.append(f"{record.temperature_k:g} K")
    if record.pressure_kpa is not None:
        parts.append(f"{record.pressure_kpa:g} kPa")
    if not parts:
        parts.append("Not recorded")
    if record.geometry_ok and record.structure_factor_ok is False:
        parts.append("geometry only")
    if record.source_origin == "bundled_example":
        parts.append("Bundled example")
    return " · ".join(parts)


class LibraryRowWidget(QWidget):
    """Presentation for one `LibraryRecord`, used via `QListWidget.setItemWidget`."""

    def __init__(self, record, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 4, 6, 4)
        outer.setSpacing(1)

        top = QHBoxLayout()
        top.setSpacing(6)
        star = "★" if record.starred else "☆"
        name_label = QLabel()
        name_label.setStyleSheet("font-weight: bold;")
        _elided(name_label, f"{star} {record.effective_display_name()}", _MAX_NAME_WIDTH_PX)
        top.addWidget(name_label)
        if record.formula:
            formula_label = QLabel()
            formula_label.setStyleSheet("color: #757575;")
            _elided(formula_label, record.formula, _MAX_FORMULA_WIDTH_PX)
            top.addWidget(formula_label)
        top.addStretch(1)
        outer.addLayout(top)

        condition_text = _condition_text(record)
        condition_label = QLabel()
        condition_label.setStyleSheet("color: #757575; font-size: 11px;")
        _elided(condition_label, condition_text, _MAX_NAME_WIDTH_PX + _MAX_FORMULA_WIDTH_PX)
        outer.addWidget(condition_label)
