"""MainWindow — QMainWindow, menu, toolbar, layout."""

from __future__ import annotations

import os

import fitz
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
)

from ..core.document import PdfDocument, PdfError
from ..core.exporter import export_images
from ..core.renderer import PageRenderer
from ..resources import icon_path
from .dialogs import AboutDialog, ExportImagesDialog, InfoDialog, InsertPdfDialog
from .page_view import FitMode, PageView
from .thumbnail_panel import ThumbnailPanel

PDF_FILTER = "PDF súbory (*.pdf)"


def app_icon() -> QIcon | None:
    path = icon_path()
    return QIcon(path) if path else None


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LizardPDF")
        self.resize(1100, 760)

        icon = app_icon()
        if icon is not None:
            self.setWindowIcon(icon)

        self.document = PdfDocument()
        self.renderer = PageRenderer(self.document)

        self.thumbnails = ThumbnailPanel(self.renderer)
        self.page_view = PageView(self.renderer)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.thumbnails)
        splitter.addWidget(self.page_view)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 880])
        self.setCentralWidget(splitter)

        self.status = self.statusBar()
        self._page_label = QLabel("")
        self.status.addPermanentWidget(self._page_label)

        self.thumbnails.page_selected.connect(self._on_thumb_selected)

        self._build_actions()
        self._build_menu()
        self._build_toolbar()
        self._update_actions_enabled()
        self._update_status()

    # ================================================================== #
    # Akcie / menu / toolbar
    # ================================================================== #
    def _build_actions(self) -> None:
        self.act_open = QAction("Otvoriť…", self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self.open_file)

        self.act_save = QAction("Uložiť", self)
        self.act_save.setShortcut(QKeySequence.StandardKey.Save)
        self.act_save.triggered.connect(self.save_file)

        self.act_save_as = QAction("Uložiť ako…", self)
        self.act_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.act_save_as.triggered.connect(self.save_file_as)

        self.act_save_opt = QAction("Uložiť ako (optimalizované)…", self)
        self.act_save_opt.triggered.connect(lambda: self.save_file_as(optimize=True))

        self.act_quit = QAction("Koniec", self)
        self.act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self.act_quit.triggered.connect(self.close)

        # navigácia
        self.act_prev = QAction("Predošlá", self)
        self.act_prev.setShortcut(QKeySequence(Qt.Key.Key_PageUp))
        self.act_prev.triggered.connect(self.prev_page)
        self.act_next = QAction("Ďalšia", self)
        self.act_next.setShortcut(QKeySequence(Qt.Key.Key_PageDown))
        self.act_next.triggered.connect(self.next_page)

        # zoom / fit
        self.act_zoom_in = QAction("Priblížiť", self)
        self.act_zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self.act_zoom_in.triggered.connect(self.page_view.zoom_in)
        self.act_zoom_out = QAction("Oddialiť", self)
        self.act_zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self.act_zoom_out.triggered.connect(self.page_view.zoom_out)
        self.act_fit_width = QAction("Na šírku", self)
        self.act_fit_width.triggered.connect(
            lambda: self.page_view.set_fit_mode(FitMode.FIT_WIDTH)
        )
        self.act_fit_page = QAction("Na stránku", self)
        self.act_fit_page.triggered.connect(
            lambda: self.page_view.set_fit_mode(FitMode.FIT_PAGE)
        )

        # page operácie
        self.act_rotate = QAction("Otočiť o 90°", self)
        self.act_rotate.setShortcut(QKeySequence("Ctrl+R"))
        self.act_rotate.triggered.connect(self.rotate_current)
        self.act_rotate_all = QAction("Otočiť všetky o 90°", self)
        self.act_rotate_all.triggered.connect(self.rotate_all)
        self.act_delete = QAction("Odstrániť stránku", self)
        self.act_delete.setShortcut(QKeySequence.StandardKey.Delete)
        self.act_delete.triggered.connect(self.delete_current)
        self.act_move_up = QAction("Posunúť hore", self)
        self.act_move_up.setShortcut(QKeySequence("Ctrl+Up"))
        self.act_move_up.triggered.connect(lambda: self.move_current(-1))
        self.act_move_down = QAction("Posunúť dole", self)
        self.act_move_down.setShortcut(QKeySequence("Ctrl+Down"))
        self.act_move_down.triggered.connect(lambda: self.move_current(1))
        self.act_duplicate = QAction("Duplikovať stránku", self)
        self.act_duplicate.triggered.connect(self.duplicate_current)

        self.act_insert = QAction("Vložiť PDF…", self)
        self.act_insert.triggered.connect(self.insert_pdf)
        self.act_extract = QAction("Extrahovať vybrané…", self)
        self.act_extract.triggered.connect(self.extract_selected)
        self.act_export = QAction("Export do obrázkov…", self)
        self.act_export.triggered.connect(self.export_images_dialog)

        self.act_info = QAction("Info o dokumente…", self)
        self.act_info.triggered.connect(self.show_info)

        self.act_about = QAction("O programe…", self)
        self.act_about.triggered.connect(self.show_about)

    def _build_menu(self) -> None:
        m = self.menuBar()
        file_menu = m.addMenu("Súbor")
        file_menu.addAction(self.act_open)
        file_menu.addSeparator()
        file_menu.addAction(self.act_save)
        file_menu.addAction(self.act_save_as)
        file_menu.addAction(self.act_save_opt)
        file_menu.addSeparator()
        file_menu.addAction(self.act_info)
        file_menu.addSeparator()
        file_menu.addAction(self.act_quit)

        view_menu = m.addMenu("Zobrazenie")
        view_menu.addAction(self.act_prev)
        view_menu.addAction(self.act_next)
        view_menu.addSeparator()
        view_menu.addAction(self.act_zoom_in)
        view_menu.addAction(self.act_zoom_out)
        view_menu.addAction(self.act_fit_width)
        view_menu.addAction(self.act_fit_page)

        page_menu = m.addMenu("Stránky")
        page_menu.addAction(self.act_rotate)
        page_menu.addAction(self.act_rotate_all)
        page_menu.addSeparator()
        page_menu.addAction(self.act_move_up)
        page_menu.addAction(self.act_move_down)
        page_menu.addAction(self.act_duplicate)
        page_menu.addAction(self.act_delete)
        page_menu.addSeparator()
        page_menu.addAction(self.act_insert)
        page_menu.addAction(self.act_extract)
        page_menu.addAction(self.act_export)

        help_menu = m.addMenu("Pomocník")
        help_menu.addAction(self.act_about)

    def _build_toolbar(self) -> None:
        tb = self.addToolBar("Hlavný panel")
        tb.setMovable(False)
        for act in (
            self.act_open,
            self.act_save,
            None,
            self.act_prev,
            self.act_next,
            None,
            self.act_zoom_out,
            self.act_zoom_in,
            self.act_fit_width,
            self.act_fit_page,
            None,
            self.act_rotate,
            self.act_delete,
            None,
            self.act_insert,
            self.act_extract,
            self.act_export,
        ):
            if act is None:
                tb.addSeparator()
            else:
                tb.addAction(act)

    # ================================================================== #
    # Súbor
    # ================================================================== #
    def open_file(self) -> None:
        if not self._maybe_save():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Otvoriť PDF", "", PDF_FILTER)
        if not path:
            return
        self._open_path(path)

    def _open_path(self, path: str) -> None:
        try:
            self.document.open(path)
        except PdfError as exc:
            # skús heslo
            if "heslom" in str(exc):
                pwd, ok = QInputDialog.getText(self, "Heslo", "Zadajte heslo k PDF:")
                if ok:
                    try:
                        self.document.open(path, password=pwd)
                    except PdfError as exc2:
                        self._error(str(exc2))
                        return
                else:
                    return
            else:
                self._error(str(exc))
                return
        self.renderer.invalidate()
        self.thumbnails.rebuild()
        self.page_view.set_page(0)
        self.thumbnails.set_current(0)
        self._update_actions_enabled()
        self._update_title()
        self._update_status()

    def save_file(self) -> None:
        if not self.document.is_open():
            return
        if self.document.path:
            self._do_save(self.document.path, optimize=False)
        else:
            self.save_file_as()

    def save_file_as(self, optimize: bool = False) -> None:
        if not self.document.is_open():
            return
        path, _ = QFileDialog.getSaveFileName(self, "Uložiť ako", "", PDF_FILTER)
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        self._do_save(path, optimize=optimize)

    def _do_save(self, path: str, optimize: bool) -> None:
        try:
            self.document.save(path, optimize=optimize)
        except PdfError as exc:
            self._error(str(exc))
            return
        # save_via_temp mohol znovu otvoriť doc → invalidovať a obnoviť
        self.renderer.invalidate()
        self.thumbnails.rebuild()
        self.page_view.refresh()
        self._update_title()
        self.status.showMessage(f"Uložené: {path}", 4000)

    # ================================================================== #
    # Navigácia
    # ================================================================== #
    def _on_thumb_selected(self, idx: int) -> None:
        self.page_view.set_page(idx)
        self._update_status()

    def prev_page(self) -> None:
        if not self.document.is_open():
            return
        idx = max(self.page_view.current_index() - 1, 0)
        self._goto(idx)

    def next_page(self) -> None:
        if not self.document.is_open():
            return
        idx = min(self.page_view.current_index() + 1, self.document.page_count() - 1)
        self._goto(idx)

    def _goto(self, idx: int) -> None:
        self.page_view.set_page(idx)
        self.thumbnails.set_current(idx)
        self._update_status()

    # ================================================================== #
    # Page operácie
    # ================================================================== #
    def rotate_current(self) -> None:
        if not self._guard():
            return
        idx = self.page_view.current_index()
        self.document.rotate_page(idx, 90)
        self.renderer.invalidate(idx)
        self.thumbnails.refresh_item(idx)
        self.page_view.refresh()
        self._after_mutation()

    def rotate_all(self) -> None:
        if not self._guard():
            return
        self.document.rotate_all(90)
        self.renderer.invalidate()
        self.thumbnails.rebuild()
        self.page_view.refresh()
        self._after_mutation()

    def delete_current(self) -> None:
        if not self._guard():
            return
        idx = self.page_view.current_index()
        try:
            self.document.delete_page(idx)
        except PdfError as exc:
            self._error(str(exc))
            return
        self.renderer.invalidate()
        self.thumbnails.rebuild()
        new_idx = min(idx, self.document.page_count() - 1)
        self._goto(new_idx)
        self._after_mutation()

    def move_current(self, direction: int) -> None:
        if not self._guard():
            return
        src = self.page_view.current_index()
        dst = src + direction
        if not 0 <= dst < self.document.page_count():
            return
        # fitz.move_page: pri posune dole treba cieľ +1 (vkladá PRED dst)
        target = dst if direction < 0 else dst + 1
        try:
            self.document.move_page(src, target)
        except PdfError as exc:
            self._error(str(exc))
            return
        self.renderer.invalidate()
        self.thumbnails.rebuild()
        self._goto(dst)
        self._after_mutation()

    def duplicate_current(self) -> None:
        if not self._guard():
            return
        idx = self.page_view.current_index()
        self.document.duplicate_page(idx)
        self.renderer.invalidate()
        self.thumbnails.rebuild()
        self._goto(idx)
        self._after_mutation()

    def insert_pdf(self) -> None:
        if not self._guard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Vložiť PDF", "", PDF_FILTER)
        if not path:
            return
        try:
            src = fitz.open(path)
            src_count = src.page_count
            needs_pass = src.needs_pass
            src.close()
        except Exception as exc:  # noqa: BLE001
            self._error(f"Súbor sa nepodarilo otvoriť: {exc}")
            return

        dlg = InsertPdfDialog(self, source_page_count=max(src_count, 1))
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        vals = dlg.values()

        password = None
        if needs_pass:
            pwd, ok = QInputDialog.getText(self, "Heslo", "Heslo k vkladanému PDF:")
            if not ok:
                return
            password = pwd

        after_idx = self.page_view.current_index()
        try:
            self.document.insert_pdf(
                path,
                after_idx=after_idx,
                from_page=vals["from_page"],
                to_page=vals["to_page"],
                password=password,
            )
        except PdfError as exc:
            self._error(str(exc))
            return
        self.renderer.invalidate()
        self.thumbnails.rebuild()
        self._goto(after_idx + 1)
        self._after_mutation()

    def extract_selected(self) -> None:
        if not self.document.is_open():
            return
        indices = self.thumbnails.selected_indices()
        if not indices:
            indices = [self.page_view.current_index()]
        path, _ = QFileDialog.getSaveFileName(
            self, "Extrahovať stránky do", "", PDF_FILTER
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            self.document.extract_pages(indices, path)
        except PdfError as exc:
            self._error(str(exc))
            return
        self.status.showMessage(
            f"Extrahované {len(indices)} stránok do {path}", 4000
        )

    def export_images_dialog(self) -> None:
        if not self.document.is_open():
            return
        selected = self.thumbnails.selected_indices()
        dlg = ExportImagesDialog(self, has_selection=bool(selected))
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        vals = dlg.values()
        out_dir = QFileDialog.getExistingDirectory(self, "Cieľový priečinok")
        if not out_dir:
            return
        if vals["only_selected"] and selected:
            indices = selected
        else:
            indices = list(range(self.document.page_count()))
        try:
            written = export_images(
                self.document, indices, out_dir, fmt=vals["fmt"], dpi=vals["dpi"]
            )
        except PdfError as exc:
            self._error(str(exc))
            return
        self.status.showMessage(
            f"Vyexportovaných {len(written)} obrázkov do {out_dir}", 4000
        )

    def show_info(self) -> None:
        if not self.document.is_open():
            return
        InfoDialog(self, info=self.document.metadata()).exec()

    def show_about(self) -> None:
        AboutDialog(self).exec()

    # ================================================================== #
    # Pomocné
    # ================================================================== #
    def _guard(self) -> bool:
        return self.document.is_open()

    def _after_mutation(self) -> None:
        self._update_title()
        self._update_status()

    def _update_actions_enabled(self) -> None:
        on = self.document.is_open()
        for act in (
            self.act_save,
            self.act_save_as,
            self.act_save_opt,
            self.act_info,
            self.act_prev,
            self.act_next,
            self.act_zoom_in,
            self.act_zoom_out,
            self.act_fit_width,
            self.act_fit_page,
            self.act_rotate,
            self.act_rotate_all,
            self.act_delete,
            self.act_move_up,
            self.act_move_down,
            self.act_duplicate,
            self.act_insert,
            self.act_extract,
            self.act_export,
        ):
            act.setEnabled(on)

    def _update_title(self) -> None:
        base = "LizardPDF"
        if self.document.is_open() and self.document.path:
            name = os.path.basename(self.document.path)
            dirty = " *" if self.document.is_dirty() else ""
            self.setWindowTitle(f"{name}{dirty} — {base}")
        else:
            self.setWindowTitle(base)

    def _update_status(self) -> None:
        if self.document.is_open():
            idx = self.page_view.current_index() + 1
            total = self.document.page_count()
            self._page_label.setText(f"Strana {idx} / {total}")
        else:
            self._page_label.setText("")

    def _error(self, msg: str) -> None:
        QMessageBox.critical(self, "Chyba", msg)

    def _maybe_save(self) -> bool:
        """Vráti False, ak používateľ akciu zrušil."""
        if not (self.document.is_open() and self.document.is_dirty()):
            return True
        ans = QMessageBox.question(
            self,
            "Neuložené zmeny",
            "Dokument obsahuje neuložené zmeny. Chcete ich uložiť?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if ans == QMessageBox.StandardButton.Save:
            self.save_file()
            return not self.document.is_dirty()
        if ans == QMessageBox.StandardButton.Cancel:
            return False
        return True  # Discard

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._maybe_save():
            self.document.close()
            event.accept()
        else:
            event.ignore()
