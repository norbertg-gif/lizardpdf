"""ThumbnailPanel — QListWidget s náhľadmi stránok."""

from __future__ import annotations

from PySide6.QtCore import QSize, QTimer, Qt, Signal
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
        self.setMinimumWidth(126)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Static)
        self.setSpacing(8)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setUniformItemSizes(True)
        self.setWordWrap(True)
        self.setStyleSheet(
            """
            QListWidget {
                background: #ffffff;
                border: 0;
                border-right: 1px solid #e4e8ec;
                padding: 10px 8px;
                color: #6f7a84;
            }
            QListWidget::item {
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px;
            }
            QListWidget::item:hover {
                background: #f3f6f8;
                border-color: #dce3e8;
            }
            QListWidget::item:selected {
                background: #f3fbf7;
                border: 1px solid #1ea672;
                color: #15845b;
            }
            QScrollBar:vertical {
                background: transparent;
                border: 0;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: #b8c0c8;
                border-radius: 4px;
                min-height: 36px;
            }
            QScrollBar::handle:vertical:hover {
                background: #98a3ad;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            """
        )
        self._rendered: set[int] = set()
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(0)
        self._render_timer.timeout.connect(self.render_visible)
        self.currentRowChanged.connect(self._on_row_changed)
        self.verticalScrollBar().valueChanged.connect(self.queue_render_visible)

    def _on_row_changed(self, row: int) -> None:
        if row >= 0:
            self.page_selected.emit(row)

    def rebuild(self) -> None:
        """Znovu poskladá všetky náhľady (po štruktúrnej zmene)."""
        prev = self.currentRow()
        self.blockSignals(True)
        self.clear()
        self._rendered.clear()
        count = self._renderer._doc.page_count() if self._renderer._doc.is_open() else 0
        for idx in range(count):
            item = QListWidgetItem(f"{idx + 1}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            item.setSizeHint(QSize(132, 184))
            self.addItem(item)
        self.blockSignals(False)
        if 0 <= prev < count:
            self.setCurrentRow(prev)
        elif count > 0:
            self.setCurrentRow(0)
        self.queue_render_visible()

    def refresh_item(self, idx: int) -> None:
        """Aktualizuje jeden náhľad (napr. po rotácii)."""
        item = self.item(idx)
        if item is None:
            return
        self._rendered.discard(idx)
        img = self._renderer.render_thumbnail(idx)
        item.setIcon(QIcon(QPixmap.fromImage(img)))
        self._rendered.add(idx)

    def selected_indices(self) -> list[int]:
        return sorted(self.row(i) for i in self.selectedItems())

    def set_current(self, idx: int) -> None:
        if 0 <= idx < self.count():
            self.setCurrentRow(idx)
            self.scrollToItem(self.item(idx), QAbstractItemView.ScrollHint.PositionAtCenter)
            self.queue_render_visible()

    def queue_render_visible(self) -> None:
        self._render_timer.start()

    def render_visible(self) -> None:
        if not self._renderer._doc.is_open() or self.count() == 0:
            return

        viewport_rect = self.viewport().rect()
        for idx in range(self.count()):
            if idx in self._rendered:
                continue
            item = self.item(idx)
            if item is None:
                continue
            rect = self.visualItemRect(item)
            if not rect.isValid() or not rect.intersects(viewport_rect):
                continue
            img = self._renderer.render_thumbnail(idx)
            item.setIcon(QIcon(QPixmap.fromImage(img)))
            self._rendered.add(idx)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.queue_render_visible()
