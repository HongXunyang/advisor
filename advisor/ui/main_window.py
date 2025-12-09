"""Main window view for Ad-VISOR."""

import os
from typing import Optional

from PyQt5.QtWidgets import (
    QAction,
    QFileDialog,
    QGridLayout,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QStackedWidget,
    QTabWidget,
    QToolBar,
    QWidget,
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon


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
        self.setWindowTitle(config.get("app_name", "Ad-VISOR"))
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
        self.addToolBar(toolbar)

        reset_action = QAction(self)
        reset_action.setText("Reset Parameters")
        reset_action.setToolTip("Return to initialization")
        reset_icon = self._icon_path("reset.png")
        if reset_icon and os.path.exists(reset_icon):
            reset_action.setIcon(QIcon(reset_icon))
        reset_action.triggered.connect(self.controller.reset_parameters)
        toolbar.addAction(reset_action)

    def _create_menu(self):
        file_menu = self.menuBar().addMenu("&File")

        open_action = QAction("&Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)

        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_file)
        file_menu.addAction(save_action)

        file_menu.addSeparator()
        reset_action = QAction("&Reset Parameters", self)
        reset_action.setShortcut("Ctrl+R")
        reset_action.triggered.connect(self.controller.reset_parameters)
        file_menu.addAction(reset_action)

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

    def show_tabs(self):
        """Switch to the main tab view."""
        self.stacked_widget.setCurrentWidget(self.tab_widget)
        self.statusBar().showMessage("Ready")

    def show_init(self):
        """Switch back to initialization view."""
        if self.init_view:
            self.stacked_widget.setCurrentWidget(self.init_view)
            self.statusBar().showMessage("Please initialize lattice parameters")

    def _open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "All Files (*);;JSON Files (*.json);;CIF Files (*.cif)"
        )
        if not file_path:
            return

        current_widget = self.tab_widget.currentWidget()
        if hasattr(current_widget, "open_file"):
            current_widget.open_file(file_path)
        else:
            self.statusBar().showMessage("Current tab does not support opening files")

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
            "About Ad-VISOR",
            "<b>Ad-VISOR</b><p>A PyQt5-based application for X-ray scattering and diffraction preparation.</p>",
        )

    def _icon_path(self, name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "resources", "icons", name)
