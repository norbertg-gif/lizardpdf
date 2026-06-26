"""Entry point — spustí QApplication a hlavné okno."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from pdf_tool.ui import MainWindow
from pdf_tool.ui.main_window import app_icon


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LizardPDF")
    icon = app_icon()
    if icon is not None:
        app.setWindowIcon(icon)
    window = MainWindow()

    # voliteľne otvor súbor z príkazového riadku
    if len(sys.argv) > 1:
        window._open_path(sys.argv[1])

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
