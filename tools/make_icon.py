"""Vygeneruje pdf_tool/assets/icon.ico z icon.png (multi-resolution).

Použitie:  python tools/make_icon.py
Vyžaduje:  pillow
"""

from __future__ import annotations

import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(HERE, "pdf_tool", "assets")
PNG = os.path.join(ASSETS, "icon.png")
ICO = os.path.join(ASSETS, "icon.ico")

SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main() -> int:
    if not os.path.exists(PNG):
        print(f"CHÝBA: {PNG} — najprv pridaj icon.png", file=sys.stderr)
        return 1
    img = Image.open(PNG).convert("RGBA")
    img.save(ICO, format="ICO", sizes=SIZES)
    print(f"OK: {ICO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
