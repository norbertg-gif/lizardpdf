# LizardPDF

Ľahká Windows utilita na prezeranie a page-level editáciu PDF. Cieľ: rýchle,
jednoduché, žiadne ťažké SDK. Nie je to Adobe Reader.

## Funkcie (v1)

- Otvoriť / zobraziť PDF — listovanie, zoom, fit-to-width / fit-to-page
- Thumbnail panel vľavo (náhľady stránok, klik = skok)
- Otočiť stránku o 90° (aj „otočiť všetky")
- Odstrániť, duplikovať a preusporiadať stránky (posun hore/dole)
- Vložiť iný PDF za zvolenú stránku (voliteľne len rozsah strán)
- Extrahovať vybrané stránky do nového PDF
- Export stránok do JPG/PNG (celý dokument alebo výber, voľba DPI)
- Info o dokumente (počet strán, rozmery, veľkosť, metadata)
- Save / Save As (+ voľba „optimalizovať") s dirty-tracking promptom

Mimo v1: tlač, editácia textu, OCR, formuláre, podpisy, anotácie.

## Architektúra

Striktné oddelenie logiky dokumentu od GUI — `core/` nepozná Qt, takže je
samostatne testovateľné.

```
pdf_tool/
├── core/
│   ├── document.py     # PdfDocument: wrapper nad fitz, všetky operácie
│   ├── renderer.py     # render stránky → QImage, LRU cache
│   └── exporter.py     # export do JPG/PNG
├── ui/
│   ├── main_window.py  # QMainWindow, menu, toolbar, layout
│   ├── page_view.py    # zobrazenie aktuálnej stránky (zoom/fit)
│   ├── thumbnail_panel.py
│   └── dialogs.py      # export / vloženie / info dialógy
main.py                 # entry point
build.spec              # PyInstaller konfig
```

## Spustenie (vývoj)

```bash
pip install -r requirements.txt
python main.py [subor.pdf]
```

## Testy

Core logika je bez Qt, testovateľná priamo cez `pytest`:

```bash
pip install pytest
python -m pytest
```

## Ikona

Zdrojová ikona je `pdf_tool/assets/icon.png` (1024×1024). Pred Windows buildom
sa z nej vygeneruje `icon.ico`:

```bash
pip install pillow
python tools/make_icon.py
```

## Build (.exe)

Windows build sa **musí** robiť na Windowse (PyInstaller nevie cross-compilovať
z Linuxu/macOS).

```bash
pip install -r requirements.txt
pip install pyinstaller pillow
python tools/make_icon.py        # vygeneruje icon.ico
pyinstaller build.spec
```

Výsledok: priečinok `dist/LizardPDF/` s `LizardPDF.exe`, beží na Windows bez
inštalácie Pythonu.

### Automatický build cez GitHub Actions

Repo obsahuje workflow `.github/workflows/build-windows.yml`, ktorý pri každom
pushi postaví app priečinok na `windows-latest`, spustí testy a priloží
`LizardPDF-windows` ako artefakt (Actions → daný beh → Artifacts).

## Tech stack

Python 3.11+ · PyMuPDF (fitz) · PySide6-Essentials (QtCore/Gui/Widgets) · PyInstaller
