"""Export stránok do JPG/PNG."""

from __future__ import annotations

import os

import fitz

from .document import PdfDocument, PdfError


def export_images(
    doc: PdfDocument,
    indices: list[int],
    out_dir: str,
    fmt: str = "jpg",
    dpi: int = 150,
) -> list[str]:
    """Vyexportuje zvolené stránky ako obrázky. Vráti zoznam ciest."""
    fmt = fmt.lower().lstrip(".")
    if fmt not in ("jpg", "jpeg", "png"):
        raise PdfError(f"Nepodporovaný formát: {fmt}")
    if not indices:
        raise PdfError("Nie sú vybrané žiadne stránky na export.")

    os.makedirs(out_dir, exist_ok=True)
    written: list[str] = []
    for idx in indices:
        page = doc.get_page(idx)
        pix = page.get_pixmap(dpi=dpi)
        # JPG nemá alfa kanál → konverzia na RGB
        if fmt in ("jpg", "jpeg") and pix.alpha:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        out_path = os.path.join(out_dir, f"page_{idx + 1}.{fmt}")
        pix.save(out_path)
        written.append(out_path)
    return written
