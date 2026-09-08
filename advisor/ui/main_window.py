"""Main window view for Advisor-Scattering."""

import os
from typing import Optional

from PyQt5.QtWidgets import (
    QAction,
    QFileDialog,
    QGridLayout,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QToolBar,
    QWidget,
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon

from advisor.ui.dialogs.change_structure_dialog import ChangeStructureDialog, change_structure_icon


class MainWindow(QMainWindow):
    """Application shell: hosts init view and feature tabs."""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        self.init_view: Optional[QWidget] = None
        self.tabs_loaded = False

        self._setup_window()
        self._build_layout()
        self._create_toolbar()
        self._create_menu()

    def _setup_window(self):
        config = getattr(self.controller, "config", {}) or {}
        self.setWindowTitle(config.get("app_name", "Advisor-Scattering"))
        window_size = config.get("window_size", {"width": 1200, "height": 800})
        self.resize(window_size.get("width", 1200), window_size.get("height", 800))

    def _build_layout(self):
        container = QWidget(self)
        self.setCentralWidget(container)

        layout = QGridLayout(container)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget, 0, 0)

        self.tab_widget = QTabWidget()
        # The hidden scientific workspace must not dictate setup's minimum
        # window size. Restore its normal sizing when that page is shown.
        self.tab_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.tab_widget.setTabPosition(QTabWidget.West)
        self.tab_widget.setIconSize(QSize(105, 80))
        self.tab_widget.setMovable(True)
        self.tab_widget.setDocumentMode(True)
        self.stacked_widget.addWidget(self.tab_widget)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Please initialize lattice parameters")

    def _create_toolbar(self):
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)

        change_structure_action = QAction(self)
        change_structure_action.setText("Change Structure…")
        change_structure_action.setIcon(change_structure_icon())
        change_structure_action.setToolTip(
            "Pick a different CIF, or start over from a blank setup"
        )
        change_structure_action.triggered.connect(self._open_change_structure_dialog)
        toolbar.addAction(change_structure_action)

        library_action = QAction(self)
        library_action.setText("My structures…")
        library_action.setToolTip("Open, star, or manage previously saved structures")
        library_action.triggered.connect(self._open_library_picker)
        toolbar.addAction(library_action)

    def _create_menu(self):
        file_menu = self.menuBar().addMenu("&File")

        open_action = QAction("&Open CIF…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_cif)
        file_menu.addAction(open_action)

        # The sole entry point for both replacing the structure and the
        # full destructive reset (its "Start over" button) -- previously a
        # separate "Reset Parameters" action duplicated this surface.
        change_structure_action = QAction(change_structure_icon(), "&Change Structure…", self)
        change_structure_action.setShortcut("Ctrl+R")
        change_structure_action.triggered.connect(self._open_change_structure_dialog)
        file_menu.addAction(change_structure_action)

        library_action = QAction("My &structures…", self)
        library_action.triggered.connect(self._open_library_picker)
        file_menu.addAction(library_action)

        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_file)
        file_menu.addAction(save_action)

        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = self.menuBar().addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def attach_init_view(self, widget: QWidget):
        """Attach the initialization view as the first stacked page."""
        self.init_view = widget
        self.stacked_widget.insertWidget(0, widget)
        self.stacked_widget.setCurrentWidget(widget)

    def add_feature_tab(self, widget: QWidget, title: str, icon_name: Optional[str] = None, tooltip: str = ""):
        """Add a feature tab to the tab widget."""
        icon_path = self._icon_path(icon_name) if icon_name else None
        if icon_path and os.path.exists(icon_path):
            self.tab_widget.addTab(widget, QIcon(icon_path), "")
        else:
            self.tab_widget.addTab(widget, title)

        index = self.tab_widget.count() - 1
        self.tab_widget.setTabToolTip(index, tooltip or title)

    def is_showing_tabs(self) -> bool:
        """Whether the feature-tabs page (rather than the init/setup page) is current."""
        return self.stacked_widget.currentWidget() is self.tab_widget

    def show_tabs(self):
        """Switch to the main tab view."""
        self.tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        if self.init_view:
            self.init_view.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.stacked_widget.setCurrentWidget(self.tab_widget)
        self.statusBar().showMessage("Ready")

    def show_init(self):
        """Switch back to initialization view."""
        if self.init_view:
            self.tab_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
            self.init_view.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            self.stacked_widget.setCurrentWidget(self.init_view)
            self.statusBar().showMessage("Please initialize lattice parameters")

    def _open_cif(self):
        """File > Open CIF… -- routes through the same shared importer as
        drag-drop/Browse/Change Structure (AppController.import_cif), not a
        per-tab file handler."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open CIF File", "", "CIF Files (*.cif *.CIF);;All Files (*)"
        )
        if not file_path:
            return

        result = self.controller.import_cif(file_path)
        timeout = 8000 if result.status == "rejected" else 5000
        self.statusBar().showMessage(result.message, timeout)

    def _open_change_structure_dialog(self):
        """The single entry point for both replacing the structure and
        starting over (via the dialog's own "Start over" button) --
        reachable from setup or any feature tab."""
        dialog = ChangeStructureDialog(self.controller, self)
        dialog.exec_()

    def _open_library_picker(self):
        """"My structures…" -- reachable from setup or any feature tab, the
        "changing structures from the working view" entry point
        (REQUIREMENT_2)."""
        from advisor.ui.dialogs.library_picker_dialog import LibraryPickerDialog

        invoking_widget = self.focusWidget()
        LibraryPickerDialog(self.controller, self).exec_()
        if invoking_widget is not None:
            invoking_widget.setFocus()

    def _save_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File", "", "All Files (*);;JSON Files (*.json)"
        )
        if not file_path:
            return

        current_widget = self.tab_widget.currentWidget()
        if hasattr(current_widget, "save_file"):
            current_widget.save_file(file_path)
        else:
            self.statusBar().showMessage("Current tab does not support saving files")

    def _show_about(self):
        QMessageBox.about(
            self,
            "About Advisor-Scattering",
            "<b>Advisor-Scattering</b><p>A PyQt5-based application for X-ray scattering and diffraction preparation.</p>",
        )

    def _icon_path(self, name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "resources", "icons", name)
