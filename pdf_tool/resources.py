"""Prístup k zabaleným zdrojom (ikona) — funguje aj v PyInstaller .exe."""

from __future__ import annotations

import os
import sys

ICON_PNG = "icon.png"
ICON_ICO = "icon.ico"


def assets_dir() -> str:
    """Priečinok s assetmi. V PyInstaller --onefile je to ``sys._MEIPASS``."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, "assets")
    return os.path.join(os.path.dirname(__file__), "assets")


def icon_path(name: str = ICON_PNG) -> str | None:
    path = os.path.join(assets_dir(), name)
    return path if os.path.exists(path) else None
