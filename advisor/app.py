"""Application bootstrap for Ad-VISOR (Advanced Visual Scattering Toolkit for Reciprocal-space)."""

import sys
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QLocale, QDir

from advisor.controllers import AppController


def load_stylesheet() -> str:
    """Load QSS stylesheet if present."""
    base_dir = Path(__file__).resolve().parent
    qss_path = base_dir / "resources" / "qss" / "styles.qss"
    if qss_path.exists():
        return qss_path.read_text(encoding="utf-8")
    return ""


def add_icon_search_path() -> None:
    """Register a Qt search path so QSS `url(icons:...)` resolves after install."""
    icons_dir = Path(__file__).resolve().parent / "resources" / "icons"
    # Debug: print warnings for missing icons to help diagnose packaging issues
    for icon_name in ("plus.svg", "minus.svg"):
        icon_path = icons_dir / icon_name
        if not icon_path.exists():
            print(f"Warning: Icon not found at {icon_path}. Icons may not display correctly.")
    QDir.addSearchPath("icons", str(icons_dir))


def main():
    """Main application entry point."""
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Ad-VISOR")
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))

    add_icon_search_path()
    app.setStyleSheet(load_stylesheet())

    controller = AppController(app)
    controller.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
