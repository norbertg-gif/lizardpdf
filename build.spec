# PyInstaller spec — build do jedného LizardPDF.exe, optimalizovaný na veľkosť
# Build:  pyinstaller build.spec
#
# Pred buildom na Windowse sa z pdf_tool/assets/icon.png vygeneruje icon.ico
# (viď tools/make_icon.py alebo CI workflow). Pre maximálne zmenšenie treba
# mať na build stroji nainštalovaný UPX (CI ho doinštaluje cez choco).

import os

block_cipher = None

ASSETS = os.path.join("pdf_tool", "assets")
ICON_ICO = os.path.join(ASSETS, "icon.ico")

# Runtime potrebuje iba malú .ico ikonu. Veľké zdrojové icon.png ostáva
# v repozitári kvôli regenerovaniu, ale do .exe sa nebalí.
datas = []
if os.path.exists(ICON_ICO):
    datas.append((ICON_ICO, "assets"))

# Qt podsystémy, ktoré appka nepoužíva. Vyhodením sa nezaťahujú do balíka.
excludes = [
    # veľké Qt moduly, ktoré nevyužívame
    "PySide6.QtNetwork",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQuick3D",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebChannel",
    "PySide6.QtWebSockets",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtSql",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtGraphs",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DAnimation",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtLocation",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtSerialBus",
    "PySide6.QtTest",
    "PySide6.QtSvgWidgets",
    "PySide6.QtSvg",
    "PySide6.QtHelp",
    "PySide6.QtDesigner",
    "PySide6.QtUiTools",
    "PySide6.QtConcurrent",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtXml",
    "PySide6.QtScxml",
    "PySide6.QtStateMachine",
    "PySide6.QtTextToSpeech",
    "PySide6.QtRemoteObjects",
    "PySide6.QtHttpServer",
    # štandardná knižnica, ktorú nepotrebujeme
    "tkinter",
    "unittest",
    "pydoc",
    "doctest",
    "test",
    "lib2to3",
    "pdb",
    "xmlrpc",
    "ftplib",
    "numpy",
    "pandas",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    cipher=block_cipher,
)


# --- Post-filter: vyhodiť Qt preklady a nepoužívané pluginy ---------------- #
# Tieto súbory PyInstaller pribalí cez Qt hook, aj keď ich nevyužívame.
_DROP_SUBSTR = [
    "/translations/",          # Qt .qm preklady (appka je po slovensky)
    "\\translations\\",
    "/qml/",                   # QML runtime
    "\\qml\\",
    "qt6qml",
    "qt6quick",
    "qt6quick3d",
    "qt6network",
    "qt6pdf",
    "qt6multimedia",
    "qt6charts",
    "qt63d",
    "qt6web",
    "qt6sql",
    "qt6designer",
    "qt6opengl",
    "/plugins/sqldrivers/",
    "\\plugins\\sqldrivers\\",
    "/plugins/multimedia/",
    "\\plugins\\multimedia\\",
    "/plugins/position/",
    "\\plugins\\position\\",
    "/plugins/sensors/",
    "\\plugins\\sensors\\",
    "/plugins/webview/",
    "\\plugins\\webview\\",
    "/plugins/qmltooling/",
    "\\plugins\\qmltooling\\",
    "/plugins/renderplugins/",
    "\\plugins\\renderplugins\\",
    "/plugins/sceneparsers/",
    "\\plugins\\sceneparsers\\",
    "/plugins/geometryloaders/",
    "\\plugins\\geometryloaders\\",
    "/plugins/networkinformation/",
    "\\plugins\\networkinformation\\",
    "/plugins/tls/",
    "\\plugins\\tls\\",
]


def _keep(dest: str) -> bool:
    low = dest.replace("\\", "/").lower()
    return not any(s.replace("\\", "/").lower() in low for s in _DROP_SUBSTR)


a.datas = [t for t in a.datas if _keep(t[0])]
a.binaries = [t for t in a.binaries if _keep(t[0])]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# UPX nepoužiť na tieto (občas korumpuje runtime DLL na Windowse).
upx_exclude = [
    "vcruntime140.dll",
    "vcruntime140_1.dll",
    "python3.dll",
    "python311.dll",
    "qwindows.dll",
]

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
    upx_exclude=upx_exclude,
    runtime_tmpdir=None,
    console=False,  # --windowed
    icon=ICON_ICO if os.path.exists(ICON_ICO) else None,
)
