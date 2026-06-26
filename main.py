"""Entry point — spustí QApplication a hlavné okno."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from pdf_tool.ui import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LizardPDF")
    window = MainWindow()

    # voliteľne otvor súbor z príkazového riadku
    if len(sys.argv) > 1:
        window._open_path(sys.argv[1])

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
