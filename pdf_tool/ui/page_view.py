"""PageView — zobrazenie aktuálnej stránky so zoomom / fit režimami."""

from __future__ import annotations

from enum import Enum, auto

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea

from ..core.renderer import PageRenderer


class FitMode(Enum):
    FIT_WIDTH = auto()
    FIT_PAGE = auto()
    CUSTOM = auto()


class PageView(QScrollArea):
    """Scroll area s QLabel, ktorý drží vyrenderovanú stránku."""

    previous_page_requested = Signal()
    next_page_requested = Signal()

    def __init__(self, renderer: PageRenderer) -> None:
        super().__init__()
        self._renderer = renderer
        self._idx = 0
        self._zoom = 1.0  # násobok base DPI pre CUSTOM
        self._fit_mode = FitMode.FIT_WIDTH
        self._base_dpi = 96
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(120)
        self._resize_timer.timeout.connect(self.refresh)

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWidget(self._label)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    # ------------------------------------------------------------------ #
    def set_page(self, idx: int) -> None:
        self._idx = idx
        self.refresh()

    def current_index(self) -> int:
        return self._idx

    def set_fit_mode(self, mode: FitMode) -> None:
        self._fit_mode = mode
        self.refresh()

    def zoom_in(self) -> None:
        self._fit_mode = FitMode.CUSTOM
        self._zoom = min(self._zoom * 1.25, 8.0)
        self.refresh()

    def zoom_out(self) -> None:
        self._fit_mode = FitMode.CUSTOM
        self._zoom = max(self._zoom / 1.25, 0.1)
        self.refresh()

    def reset_zoom(self) -> None:
        self._zoom = 1.0
        self._fit_mode = FitMode.FIT_WIDTH
        self.refresh()

    # ------------------------------------------------------------------ #
    def _compute_dpi(self) -> int:
        try:
            page = self._renderer._doc.get_page(self._idx)
        except Exception:
            return self._base_dpi
        rect = page.rect
        # Veľkosti stránky sú v bodoch (72 dpi). Dostupný priestor:
        avail_w = max(self.viewport().width() - 24, 100)
        avail_h = max(self.viewport().height() - 24, 100)

        if self._fit_mode == FitMode.CUSTOM:
            return max(int(self._base_dpi * self._zoom), 10)

        # zohľadni rotáciu (na/výška sa prehodí pri 90/270)
        w_pt, h_pt = rect.width, rect.height
        if page.rotation in (90, 270):
            w_pt, h_pt = h_pt, w_pt

        dpi_w = avail_w / (w_pt / 72.0)
        if self._fit_mode == FitMode.FIT_WIDTH:
            dpi = dpi_w
        else:  # FIT_PAGE
            dpi_h = avail_h / (h_pt / 72.0)
            dpi = min(dpi_w, dpi_h)
        return max(min(int(dpi), 600), 10)

    def refresh(self) -> None:
        if not self._renderer._doc.is_open():
            self._label.clear()
            return
        if not 0 <= self._idx < self._renderer._doc.page_count():
            self._label.clear()
            return
        dpi = self._compute_dpi()
        img = self._renderer.render_page(self._idx, dpi=dpi)
        self._label.setPixmap(QPixmap.fromImage(img))
        self._label.resize(img.size())

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().resizeEvent(event)
        if self._fit_mode != FitMode.CUSTOM:
            self._resize_timer.start()

    def wheelEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        bar = self.verticalScrollBar()
        delta = event.angleDelta().y()
        at_top = bar.value() <= bar.minimum()
        at_bottom = bar.value() >= bar.maximum()

        if delta > 0 and at_top:
            self.previous_page_requested.emit()
            event.accept()
            return
        if delta < 0 and at_bottom:
            self.next_page_requested.emit()
            event.accept()
            return

        super().wheelEvent(event)
