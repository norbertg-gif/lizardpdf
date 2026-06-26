# PyInstaller spec — build do jedného PdfTool.exe (LizardPDF)
# Build:  pyinstaller build.spec
#
# Pred buildom na Windowse sa z pdf_tool/assets/icon.png vygeneruje icon.ico
# (viď tools/make_icon.py alebo CI workflow).

import os

block_cipher = None

ASSETS = os.path.join("pdf_tool", "assets")
ICON_ICO = os.path.join(ASSETS, "icon.ico")

# zabalené dáta: priečinok assets → do "assets" v balíku (sys._MEIPASS/assets)
datas = []
if os.path.isdir(ASSETS):
    for fn in os.listdir(ASSETS):
        datas.append((os.path.join(ASSETS, fn), "assets"))

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="LizardPDF",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,  # --windowed
    icon=ICON_ICO if os.path.exists(ICON_ICO) else None,
)
