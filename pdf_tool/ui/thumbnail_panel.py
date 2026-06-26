"""ThumbnailPanel — QListWidget s náhľadmi stránok."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QAbstractItemView, QListWidget, QListWidgetItem

from ..core.renderer import PageRenderer


class ThumbnailPanel(QListWidget):
    """Panel náhľadov. Emituje page_selected pri zmene aktuálnej stránky."""

    page_selected = Signal(int)

    def __init__(self, renderer: PageRenderer) -> None:
        super().__init__()
        self._renderer = renderer
        self.setIconSize(QSize(120, 160))
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Static)
        self.setSpacing(6)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setUniformItemSizes(True)
        self.setWordWrap(True)
        self.currentRowChanged.connect(self._on_row_changed)

    def _on_row_changed(self, row: int) -> None:
        if row >= 0:
            self.page_selected.emit(row)

    def rebuild(self) -> None:
        """Znovu poskladá všetky náhľady (po štruktúrnej zmene)."""
        prev = self.currentRow()
        self.blockSignals(True)
        self.clear()
        count = self._renderer._doc.page_count() if self._renderer._doc.is_open() else 0
        for idx in range(count):
            item = QListWidgetItem(f"{idx + 1}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            img = self._renderer.render_thumbnail(idx)
            item.setIcon(QIcon(QPixmap.fromImage(img)))
            self.addItem(item)
        self.blockSignals(False)
        if 0 <= prev < count:
            self.setCurrentRow(prev)
        elif count > 0:
            self.setCurrentRow(0)

    def refresh_item(self, idx: int) -> None:
        """Aktualizuje jeden náhľad (napr. po rotácii)."""
        item = self.item(idx)
        if item is None:
            return
        img = self._renderer.render_thumbnail(idx)
        item.setIcon(QIcon(QPixmap.fromImage(img)))

    def selected_indices(self) -> list[int]:
        return sorted(self.row(i) for i in self.selectedItems())

    def set_current(self, idx: int) -> None:
        if 0 <= idx < self.count():
            self.setCurrentRow(idx)
