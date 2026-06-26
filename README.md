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

## Build (.exe)

```bash
pip install pymupdf pyside6 pyinstaller
pyinstaller build.spec
# alebo:
pyinstaller --onefile --windowed --name PdfTool main.py
```

Výsledok: jediné `dist/PdfTool.exe`, beží na Windows bez inštalácie Pythonu.

## Tech stack

Python 3.11+ · PyMuPDF (fitz) · PySide6 (Qt) · PyInstaller
