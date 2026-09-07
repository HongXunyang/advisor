"""Shared CIF selection and structure-summary widgets.

`CifDropTarget` is the single place drag-and-drop / Browse selection logic
lives -- both the init/setup view and the "Change Structure…" dialog embed
one instance, so browse/drop/menu all funnel through the same deliberate
`cifSelected` signal (never `textChanged`), guaranteeing one user action
produces exactly one import attempt.

`CifStructureSummary` is a purely presentational readout of whatever
`CifImportResult`/`StructureSource` the consumer (e.g. `AppController`) most
recently produced -- it holds no import logic of its own.
"""

import os

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_STATUS_COLORS = {
    "ready": "#2d5a3d",
    "ready_geometry_only": "#8a6d3b",
    "rejected": "#C62828",
    "unchanged": "#2d5a3d",
    "empty": "#757575",
}


class CifDropTarget(QWidget):
    """Drag-and-drop + Browse area for selecting one CIF file.

    Emits `cifSelected(path)` exactly once for a deliberate, well-formed
    single-file selection (case-insensitive `.cif`, local file, not a
    folder). Emits `selectionRejected(message)` for anything this widget can
    reject on the spot (multiple files, a folder, a non-local URL, or the
    wrong extension) -- deeper CIF-content validation happens downstream and
    is reported back to whoever calls `AppController.import_cif()`, not by
    this widget.
    """

    cifSelected = pyqtSignal(str)
    selectionRejected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._display = QLineEdit()
        self._display.setReadOnly(True)
        self._display.setPlaceholderText("Drag and drop a .cif file here, or Browse…")
        layout.addWidget(self._display)

        browse_button = QPushButton("Browse…")
        browse_button.clicked.connect(self._on_browse_clicked)
        layout.addWidget(browse_button)

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls() and any(url.isLocalFile() for url in mime.urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        event.acceptProposedAction()

        local_paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
        if not local_paths or len(local_paths) != len(urls):
            self.selectionRejected.emit("Only local files can be dropped here.")
            return
        if len(local_paths) > 1:
            self.selectionRejected.emit(
                f"{len(local_paths)} files were dropped. Please choose a single .cif file."
            )
            return

        path = local_paths[0]
        if os.path.isdir(path):
            self.selectionRejected.emit(
                f"'{os.path.basename(path)}' is a folder, not a CIF file."
            )
            return
        if os.path.splitext(path)[1].lower() != ".cif":
            self.selectionRejected.emit(
                f"'{os.path.basename(path)}' is not a .cif file."
            )
            return

        self._select(path)

    def _on_browse_clicked(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open CIF File", "", "CIF Files (*.cif *.CIF);;All Files (*)"
        )
        if path:
            self._select(path)

    def _select(self, path: str):
        # Deliberately does not display `path` here (e.g. via
        # self._display.setText(path)): this widget only proposes a
        # candidate -- validation/acceptance happens downstream in
        # AppController.import_cif() -- and a candidate that's later
        # rejected must not be left looking like "the currently loaded
        # file." What's actually accepted is CifStructureSummary's concern;
        # this field always stays at its placeholder.
        self.cifSelected.emit(path)


class CifStructureSummary(QWidget):
    """Compact, always-visible readout of the currently accepted structure.

    Shows a friendly name (filename fallback) + formula + capability status
    inline, eliding long names rather than growing the layout. Path, full
    cell, space group, and source detail are deliberately not shown here --
    see the on-demand `CifDetailsDialog` for that.
    """

    detailsRequested = pyqtSignal()
    useManualLatticeRequested = pyqtSignal()
    removeStructureRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 4, 0, 0)
        outer.setSpacing(2)

        self._name_label = QLabel("No structure loaded")
        self._name_label.setStyleSheet("font-weight: bold;")
        outer.addWidget(self._name_label)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        outer.addWidget(self._status_label)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 2, 0, 0)

        self._details_button = QPushButton("Details…")
        self._details_button.clicked.connect(self.detailsRequested.emit)
        self._details_button.setVisible(False)
        actions.addWidget(self._details_button)

        self._manual_button = QPushButton("Use manual lattice")
        self._manual_button.clicked.connect(self.useManualLatticeRequested.emit)
        self._manual_button.setVisible(False)
        actions.addWidget(self._manual_button)

        self._remove_button = QPushButton("Remove CIF")
        self._remove_button.clicked.connect(self.removeStructureRequested.emit)
        self._remove_button.setVisible(False)
        actions.addWidget(self._remove_button)

        actions.addStretch(1)
        outer.addLayout(actions)

        self._full_name_text = ""
        self._source = None

    def current_source(self):
        return self._source

    def set_empty(self):
        """No structure accepted -- initial state, or after Remove CIF."""
        self._source = None
        self._name_label.setText("No structure loaded")
        self._full_name_text = ""
        self._set_status("Provide a CIF or enter lattice parameters manually.", "empty")
        self._details_button.setVisible(False)
        self._manual_button.setVisible(False)
        self._remove_button.setVisible(False)

    def set_source(self, source):
        """Display an accepted `StructureSource` (CIF-derived or manual)."""
        self._source = source
        name = source.display_name
        if source.formula:
            name = f"{name} ({source.formula})"
        self._full_name_text = name
        self._name_label.setText(self._elided(name))
        self._name_label.setToolTip(name)
        if source.capabilities.structure_factor_ok:
            status_key = "ready"
        elif source.capabilities.geometry_ok:
            status_key = "ready_geometry_only"
        else:
            status_key = "rejected"
        self._set_status(source.capabilities.message, status_key)

        is_cif = source.source_kind == "cif"
        self._details_button.setVisible(True)
        self._manual_button.setVisible(is_cif)
        self._remove_button.setVisible(is_cif)

    def set_rejected(self, message: str):
        """A candidate was rejected -- the accepted structure (if any) is
        unchanged, so this only flashes a transient status message."""
        self._set_status(message, "rejected")

    def _set_status(self, message: str, status_key: str):
        color = _STATUS_COLORS.get(status_key, _STATUS_COLORS["empty"])
        self._status_label.setStyleSheet(f"color: {color};")
        self._status_label.setText(message)

    def _elided(self, text: str) -> str:
        metrics = QFontMetrics(self._name_label.font())
        max_width = max(self.width(), 220)
        return metrics.elidedText(text, Qt.ElideMiddle, max_width)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._full_name_text:
            self._name_label.setText(self._elided(self._full_name_text))
