"""Dialógy — export obrázkov, vloženie PDF, info o dokumente, o programe."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from .. import __version__
from ..resources import icon_path


class ExportImagesDialog(QDialog):
    """Voľby pre export do JPG/PNG: formát, DPI, rozsah."""

    def __init__(self, parent=None, has_selection: bool = False) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export do obrázkov")

        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["JPG", "PNG"])

        self.dpi_combo = QComboBox()
        self.dpi_combo.addItems(["72", "150", "300", "600"])
        self.dpi_combo.setCurrentText("150")
        self.dpi_combo.setEditable(True)

        self.rb_all = QRadioButton("Všetky stránky")
        self.rb_sel = QRadioButton("Iba vybrané stránky")
        if has_selection:
            self.rb_sel.setChecked(True)
        else:
            self.rb_all.setChecked(True)
            self.rb_sel.setEnabled(False)

        form = QFormLayout()
        form.addRow("Formát:", self.fmt_combo)
        form.addRow("DPI:", self.dpi_combo)
        form.addRow(self.rb_all)
        form.addRow(self.rb_sel)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> dict:
        return {
            "fmt": self.fmt_combo.currentText().lower(),
            "dpi": int(self.dpi_combo.currentText() or "150"),
            "only_selected": self.rb_sel.isChecked(),
        }


class InsertPdfDialog(QDialog):
    """Voľba rozsahu strán vkladaného PDF (1-based, vrátane)."""

    def __init__(self, parent=None, source_page_count: int = 1) -> None:
        super().__init__(parent)
        self.setWindowTitle("Vložiť PDF — rozsah strán")
        self._count = source_page_count

        self.rb_all = QRadioButton("Všetky stránky")
        self.rb_all.setChecked(True)
        self.rb_range = QRadioButton("Rozsah strán:")

        self.from_spin = QSpinBox()
        self.from_spin.setRange(1, source_page_count)
        self.from_spin.setValue(1)
        self.to_spin = QSpinBox()
        self.to_spin.setRange(1, source_page_count)
        self.to_spin.setValue(source_page_count)

        form = QFormLayout()
        form.addRow(self.rb_all)
        form.addRow(self.rb_range)
        form.addRow("Od:", self.from_spin)
        form.addRow("Do:", self.to_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Vkladaný dokument má {source_page_count} stránok."))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> dict:
        if self.rb_all.isChecked():
            return {"from_page": None, "to_page": None}
        a = self.from_spin.value() - 1
        b = self.to_spin.value() - 1
        if a > b:
            a, b = b, a
        return {"from_page": a, "to_page": b}


class InfoDialog(QDialog):
    """Zobrazí metadata dokumentu."""

    def __init__(self, parent=None, info: dict | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Informácie o dokumente")
        self.resize(460, 380)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(self._format(info or {}))
        layout = QVBoxLayout(self)
        layout.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    @staticmethod
    def _format(info: dict) -> str:
        lines: list[str] = []
        lines.append(f"Súbor: {info.get('path') or '—'}")
        lines.append(f"Počet strán: {info.get('page_count', '—')}")

        size = info.get("file_size")
        if size is not None:
            lines.append(f"Veľkosť súboru: {size / 1024:.1f} kB")

        sizes = info.get("page_sizes") or []
        if sizes:
            unique = sorted(set(sizes))
            if len(unique) == 1:
                w, h = unique[0]
                lines.append(f"Rozmery stránok: {w} × {h} bodov")
            else:
                lines.append("Rozmery stránok: rôzne")
                for i, (w, h) in enumerate(sizes[:20], start=1):
                    lines.append(f"   strana {i}: {w} × {h}")
                if len(sizes) > 20:
                    lines.append("   …")

        meta = info.get("metadata") or {}
        if meta:
            lines.append("")
            lines.append("Metadata:")
            for key, val in meta.items():
                if val:
                    lines.append(f"   {key}: {val}")
        return "\n".join(lines)


class MetadataEditDialog(QDialog):
    """Úprava základných PDF metadát."""

    FIELDS = (
        ("title", "Názov"),
        ("author", "Autor"),
        ("subject", "Predmet"),
        ("keywords", "Kľúčové slová"),
        ("creator", "Vytvoril"),
        ("producer", "Producent"),
    )

    def __init__(self, parent=None, metadata: dict | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Upraviť metadata")
        self.setMinimumWidth(420)
        metadata = metadata or {}
        self.edits: dict[str, QLineEdit] = {}

        form = QFormLayout()
        for key, label in self.FIELDS:
            edit = QLineEdit(str(metadata.get(key) or ""))
            self.edits[key] = edit
            form.addRow(f"{label}:", edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> dict[str, str]:
        return {key: edit.text() for key, edit in self.edits.items()}


class TextStampDialog(QDialog):
    """Voľby pre textovú pečiatku alebo číslovanie strán."""

    def __init__(self, parent=None, has_selection: bool = False) -> None:
        super().__init__(parent)
        self.setWindowTitle("Text na stránky")
        self.setMinimumWidth(380)

        self.rb_stamp = QRadioButton("Textová pečiatka")
        self.rb_stamp.setChecked(True)
        self.rb_numbers = QRadioButton("Čísla strán")

        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("Napr. Kópia")
        self.prefix_edit = QLineEdit("Strana")

        self.size_spin = QSpinBox()
        self.size_spin.setRange(6, 72)
        self.size_spin.setValue(10)

        self.selection_check = QCheckBox("Použiť iba vybrané stránky")
        self.selection_check.setEnabled(has_selection)
        self.selection_check.setChecked(has_selection)

        form = QFormLayout()
        form.addRow(self.rb_stamp)
        form.addRow("Text:", self.text_edit)
        form.addRow(self.rb_numbers)
        form.addRow("Prefix:", self.prefix_edit)
        form.addRow("Veľkosť:", self.size_spin)
        form.addRow(self.selection_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> dict:
        return {
            "mode": "numbers" if self.rb_numbers.isChecked() else "stamp",
            "text": self.text_edit.text(),
            "prefix": self.prefix_edit.text() or "Strana",
            "font_size": self.size_spin.value(),
            "only_selected": self.selection_check.isChecked(),
        }


class AboutDialog(QDialog):
    """O programe — názov, verzia, autor, použité technológie."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("O programe LizardPDF")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # logo + názov vedľa seba
        header = QHBoxLayout()
        header.setSpacing(16)

        logo = QLabel()
        path = icon_path()
        if path:
            pix = QIcon(path).pixmap(96, 96)
            logo.setPixmap(pix)
        header.addWidget(logo, 0, Qt.AlignmentFlag.AlignTop)

        title = QLabel(
            f"<h2 style='margin:0'>LizardPDF</h2>"
            f"<p style='margin:2px 0'>Verzia {__version__}</p>"
            f"<p style='margin:2px 0;color:gray'>Ľahká utilita na prezeranie "
            f"a editáciu PDF na úrovni stránok.</p>"
        )
        title.setTextFormat(Qt.TextFormat.RichText)
        title.setWordWrap(True)
        header.addWidget(title, 1)
        layout.addLayout(header)

        info = QLabel(
            "<hr>"
            "<p><b>Vibecoded by DigitalDreams</b></p>"
            "<p style='color:gray'>Postavené na Pythone, PySide6 (Qt) "
            "a PyMuPDF.</p>"
            "<p style='color:gray'>© 2026 DigitalDreams. Všetky práva "
            "vyhradené.</p>"
        )
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setWordWrap(True)
        info.setOpenExternalLinks(True)
        layout.addWidget(info)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
