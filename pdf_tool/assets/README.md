# assets

Sem patrí ikona aplikácie:

- `icon.png` — zdrojová ikona (ideálne 1024×1024, RGBA). Používa sa ako ikona
  okna a tray ikona.
- `icon.ico` — vygeneruje sa automaticky z `icon.png` cez
  `python tools/make_icon.py` (potrebné len pre Windows `.exe`).

Ak `icon.png` chýba, aplikácia beží normálne, len bez vlastnej ikony.
