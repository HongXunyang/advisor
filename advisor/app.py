"""Application bootstrap for Advisor-Scattering (Advanced Visual Scattering Toolkit for Reciprocal-space)."""

import os
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QLocale, QFile, QIODevice

from advisor.controllers import AppController
from advisor.resources import resources_rc


def load_stylesheet() -> str:
    """Load QSS stylesheet if present."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    qss_path = os.path.join(base_dir, "resources", "qss", "styles.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as handle:
            return handle.read()
    return ""


def main():
    """Main application entry point."""
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Advisor-Scattering")
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    app.setStyleSheet(load_stylesheet())


    controller = AppController(app)
    controller.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
