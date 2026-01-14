"""Application bootstrap for Ad-VISOR (Advanced Visual Scattering Toolkit for Reciprocal-space)."""

import sys
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QLocale

from advisor.controllers import AppController


def _icon_path(name: str) -> str:
    """Return absolute path to an icon in the resources/icons folder."""
    return str(Path(__file__).resolve().parent / "resources" / "icons" / name)


def load_stylesheet() -> str:
    """Load QSS stylesheet and resolve icon paths."""
    base_dir = Path(__file__).resolve().parent
    qss_path = base_dir / "resources" / "qss" / "styles.qss"
    if not qss_path.exists():
        return ""
    
    qss = qss_path.read_text(encoding="utf-8")
    # Replace icon placeholders with absolute paths
    qss = qss.replace("{{PLUS_ICON}}", _icon_path("plus.svg"))
    qss = qss.replace("{{MINUS_ICON}}", _icon_path("minus.svg"))
    return qss


def main():
    """Main application entry point."""
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Ad-VISOR")
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))

    app.setStyleSheet(load_stylesheet())

    controller = AppController(app)
    controller.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
