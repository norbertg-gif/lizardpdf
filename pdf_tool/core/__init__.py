"""Core vrstva — logika dokumentu, nezávislá od GUI.

``document`` a ``exporter`` nepotrebujú Qt (sú testovateľné samostatne).
``renderer`` závisí od PySide6 a importuje sa explicitne tam, kde treba.
"""

from .document import PdfDocument, PdfError
from .exporter import export_images

__all__ = [
    "PdfDocument",
    "PdfError",
    "export_images",
]
