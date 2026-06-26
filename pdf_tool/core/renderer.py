"""Renderer — render stránky na QImage s LRU cache.

Renderuje on-demand. Pri zoome sa mení DPI (nie škálovanie hotového
obrázka) kvôli ostrosti. Po každej page-operácii treba zavolať
``invalidate()`` (najjednoduchšie celý cache).
"""

from __future__ import annotations

from collections import OrderedDict

import fitz
from PySide6.QtGui import QImage

from .document import PdfDocument


def pixmap_to_qimage(pix: fitz.Pixmap) -> QImage:
    """fitz.Pixmap → QImage. Pozor na stride a na alfa kanál."""
    if pix.alpha:
        fmt = QImage.Format.Format_RGBA8888
    else:
        fmt = QImage.Format.Format_RGB888
    img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
    # samples je dočasný buffer → spravíme hlbokú kópiu
    return img.copy()


class PageRenderer:
    def __init__(self, doc: PdfDocument, cache_size: int = 10) -> None:
        self._doc = doc
        self._cache_size = cache_size
        # kľúč: (idx, dpi) → QImage
        self._cache: OrderedDict[tuple[int, int], QImage] = OrderedDict()
        self._thumb_cache: OrderedDict[int, QImage] = OrderedDict()
        self._thumb_max = 200

    def render_page(self, idx: int, dpi: int = 96) -> QImage:
        key = (idx, dpi)
        cached = self._cache.get(key)
        if cached is not None:
            self._cache.move_to_end(key)
            return cached

        page = self._doc.get_page(idx)
        pix = page.get_pixmap(dpi=dpi)
        img = pixmap_to_qimage(pix)

        self._cache[key] = img
        self._cache.move_to_end(key)
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return img

    def render_thumbnail(self, idx: int, dpi: int = 40) -> QImage:
        cached = self._thumb_cache.get(idx)
        if cached is not None:
            self._thumb_cache.move_to_end(idx)
            return cached

        page = self._doc.get_page(idx)
        pix = page.get_pixmap(dpi=dpi)
        img = pixmap_to_qimage(pix)

        self._thumb_cache[idx] = img
        self._thumb_cache.move_to_end(idx)
        while len(self._thumb_cache) > self._thumb_max:
            self._thumb_cache.popitem(last=False)
        return img

    def invalidate(self, idx: int | None = None) -> None:
        """Zahodí cache. ``idx=None`` → všetko (po delete/move sa
        posúvajú indexy, takže zvyčajne chceme všetko)."""
        if idx is None:
            self._cache.clear()
            self._thumb_cache.clear()
            return
        self._cache = OrderedDict(
            (k, v) for k, v in self._cache.items() if k[0] != idx
        )
        self._thumb_cache.pop(idx, None)
