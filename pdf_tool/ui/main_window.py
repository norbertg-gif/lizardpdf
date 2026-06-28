"""MainWindow — QMainWindow, menu, toolbar, layout."""

from __future__ import annotations

import os

import fitz
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStyle,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..core.document import PdfDocument, PdfError
from ..core.exporter import export_images
from ..core.renderer import PageRenderer
from ..resources import icon_path
from .dialogs import (
    AboutDialog,
    ExportImagesDialog,
    InfoDialog,
    InsertPdfDialog,
    MetadataEditDialog,
    TextStampDialog,
)
from .page_view import FitMode, PageView
from .thumbnail_panel import ThumbnailPanel

PDF_FILTER = "PDF súbory (*.pdf)"
MERGE_FILTER = "PDF a JPG súbory (*.pdf *.jpg *.jpeg);;PDF súbory (*.pdf);;JPG obrázky (*.jpg *.jpeg)"


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
        self._last_search = ""

        self.thumbnails = ThumbnailPanel(self.renderer)
        self.page_view = PageView(self.renderer)
        self._doc_label = QLabel("Žiadny dokument")
        self._doc_label.setObjectName("documentTitle")

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("documentSplitter")
        splitter.addWidget(self.thumbnails)
        splitter.addWidget(self.page_view)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)
        splitter.setSizes([170, 930])

        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(16, 0, 16, 0)
        topbar_layout.setSpacing(8)
        crumb = QLabel("Dokumenty /")
        crumb.setObjectName("breadcrumb")
        topbar_layout.addWidget(crumb)
        topbar_layout.addWidget(self._doc_label, 1)

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(topbar)
        central_layout.addWidget(splitter, 1)
        self.setCentralWidget(central)

        self.status = self.statusBar()
        self._page_label = QLabel("")
        self.status.addPermanentWidget(self._page_label)

        self.thumbnails.page_selected.connect(self._on_thumb_selected)
        self.page_view.previous_page_requested.connect(self.prev_page)
        self.page_view.next_page_requested.connect(self.next_page)

        self._build_actions()
        self._build_menu()
        self._build_toolbar()
        self._apply_style()
        self._update_actions_enabled()
        self._update_title()
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

        self.act_revert = QAction("Vrátiť posledne uložené", self)
        self.act_revert.triggered.connect(self.revert_to_saved)

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
        self.act_find = QAction("Hľadať text…", self)
        self.act_find.setShortcut(QKeySequence.StandardKey.Find)
        self.act_find.triggered.connect(self.find_text)
        self.act_find_next = QAction("Hľadať ďalej", self)
        self.act_find_next.setShortcut(QKeySequence.StandardKey.FindNext)
        self.act_find_next.triggered.connect(self.find_next)
        self.act_copy_text = QAction("Kopírovať text stránky", self)
        self.act_copy_text.setShortcut(QKeySequence.StandardKey.Copy)
        self.act_copy_text.triggered.connect(self.copy_current_page_text)

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
        self.act_merge = QAction("Pripojiť/spojiť PDF a JPG…", self)
        self.act_merge.triggered.connect(self.merge_pdfs)
        self.act_extract = QAction("Extrahovať vybrané…", self)
        self.act_extract.triggered.connect(self.extract_selected)
        self.act_export = QAction("Export do obrázkov…", self)
        self.act_export.triggered.connect(self.export_images_dialog)

        self.act_info = QAction("Info o dokumente…", self)
        self.act_info.triggered.connect(self.show_info)
        self.act_edit_metadata = QAction("Upraviť metadata…", self)
        self.act_edit_metadata.triggered.connect(self.edit_metadata)

        self.act_about = QAction("O programe…", self)
        self.act_about.triggered.connect(self.show_about)
        self.act_text_stamp = QAction("Text na stránky…", self)
        self.act_text_stamp.triggered.connect(self.text_stamp_dialog)

    def _build_menu(self) -> None:
        m = self.menuBar()
        file_menu = m.addMenu("Súbor")
        file_menu.addAction(self.act_open)
        file_menu.addSeparator()
        file_menu.addAction(self.act_save)
        file_menu.addAction(self.act_save_as)
        file_menu.addAction(self.act_save_opt)
        file_menu.addAction(self.act_revert)
        file_menu.addSeparator()
        file_menu.addAction(self.act_info)
        file_menu.addAction(self.act_edit_metadata)
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
        view_menu.addSeparator()
        view_menu.addAction(self.act_find)
        view_menu.addAction(self.act_find_next)
        view_menu.addAction(self.act_copy_text)

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
        page_menu.addAction(self.act_merge)
        page_menu.addAction(self.act_extract)
        page_menu.addAction(self.act_export)
        page_menu.addSeparator()
        page_menu.addAction(self.act_text_stamp)

        help_menu = m.addMenu("Pomocník")
        help_menu.addAction(self.act_about)

    def _build_toolbar(self) -> None:
        tb = QToolBar("Nástroje", self)
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setIconSize(QSize(20, 20))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, tb)

        style = self.style()
        icons = {
            self.act_open: QStyle.StandardPixmap.SP_DialogOpenButton,
            self.act_save: QStyle.StandardPixmap.SP_DialogSaveButton,
            self.act_prev: QStyle.StandardPixmap.SP_ArrowBack,
            self.act_next: QStyle.StandardPixmap.SP_ArrowForward,
            self.act_zoom_out: QStyle.StandardPixmap.SP_ArrowDown,
            self.act_zoom_in: QStyle.StandardPixmap.SP_ArrowUp,
            self.act_fit_width: QStyle.StandardPixmap.SP_ArrowLeft,
            self.act_fit_page: QStyle.StandardPixmap.SP_DialogApplyButton,
            self.act_rotate: QStyle.StandardPixmap.SP_BrowserReload,
            self.act_delete: QStyle.StandardPixmap.SP_TrashIcon,
            self.act_insert: QStyle.StandardPixmap.SP_FileDialogNewFolder,
            self.act_extract: QStyle.StandardPixmap.SP_DialogSaveButton,
            self.act_export: QStyle.StandardPixmap.SP_DriveHDIcon,
        }
        for act, pixmap in icons.items():
            act.setIcon(style.standardIcon(pixmap))
            act.setToolTip(act.text().replace("&", ""))

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

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f4f6f7;
            }
            QMenuBar {
                background: #ffffff;
                border-bottom: 1px solid #e6eaee;
                padding: 2px 8px;
            }
            QMenuBar::item {
                padding: 5px 10px;
                border-radius: 5px;
            }
            QMenuBar::item:selected {
                background: #eef3f1;
            }
            QFrame#topbar {
                min-height: 42px;
                max-height: 42px;
                background: #ffffff;
                border-bottom: 1px solid #e4e8ec;
            }
            QLabel#breadcrumb {
                color: #77818c;
                font-size: 12px;
            }
            QLabel#documentTitle {
                color: #2c333a;
                font-weight: 600;
            }
            QToolBar {
                background: #ffffff;
                border-right: 1px solid #e4e8ec;
                spacing: 4px;
                padding: 8px 6px;
            }
            QToolBar::separator {
                background: #e4e8ec;
                height: 1px;
                margin: 6px 8px;
            }
            QToolButton {
                border: 0;
                border-radius: 7px;
                padding: 7px;
                min-width: 30px;
                min-height: 30px;
            }
            QToolButton:hover {
                background: #eef3f1;
            }
            QToolButton:pressed {
                background: #dff3ea;
            }
            QStatusBar {
                background: #ffffff;
                border-top: 1px solid #e4e8ec;
                color: #68737d;
            }
            QSplitter#documentSplitter::handle {
                background: #edf0f3;
                width: 6px;
            }
            QSplitter#documentSplitter::handle:hover {
                background: #cfd8df;
            }
            """
        )

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
        self.page_view.set_page(0)
        self.thumbnails.rebuild()
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
    def revert_to_saved(self) -> None:
        if not self.document.is_open():
            return
        if not self.document.path:
            self._error("Dokument ešte nebol uložený na disk.")
            return
        ans = QMessageBox.question(
            self,
            "Revert",
            "Zahodiť všetky neuložené zmeny a načítať posledne uložený súbor?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        idx = self.page_view.current_index()
        try:
            self.document.reload()
        except PdfError as exc:
            self._error(str(exc))
            return
        self.renderer.invalidate()
        self.thumbnails.rebuild()
        self._goto(min(idx, self.document.page_count() - 1))
        self._update_actions_enabled()
        self._update_title()
        self.status.showMessage("Obnovené z posledne uloženého súboru.", 4000)

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

    def find_text(self) -> None:
        if not self.document.is_open():
            return
        text, ok = QInputDialog.getText(self, "Hľadať text", "Text:", text=self._last_search)
        if not ok:
            return
        self._last_search = text.strip()
        self._find_from(self.page_view.current_index())

    def find_next(self) -> None:
        if not self.document.is_open():
            return
        if not self._last_search:
            self.find_text()
            return
        self._find_from(self.page_view.current_index() + 1)

    def _find_from(self, start_idx: int) -> None:
        try:
            found = self.document.search_text(self._last_search, start_idx=start_idx)
        except PdfError as exc:
            self._error(str(exc))
            return
        if found is None:
            self.page_view.set_highlight_query("")
            if not self.document.has_text():
                self.status.showMessage("Dokument nemá extrahovateľnú textovú vrstvu.", 5000)
                return
            self.status.showMessage(f"Nenájdené: {self._last_search}", 4000)
            return
        self.page_view.set_highlight_query(self._last_search)
        self._goto(found)
        self.status.showMessage(f"Nájdené na strane {found + 1}: {self._last_search}", 4000)

    def copy_current_page_text(self) -> None:
        if not self.document.is_open():
            return
        try:
            text = self.document.page_text(self.page_view.current_index())
        except PdfError as exc:
            self._error(str(exc))
            return
        if not text.strip():
            self.status.showMessage("Aktuálna stránka nemá extrahovateľný text.", 5000)
            return
        QApplication.clipboard().setText(text)
        self.status.showMessage("Text aktuálnej stránky je v schránke.", 4000)

    # ================================================================== #
    # Page operácie
    # ================================================================== #
    def rotate_current(self) -> None:
        if not self._guard():
            return
        indices = self._target_page_indices()
        self.document.rotate_pages(indices, 90)
        self.renderer.invalidate()
        self.thumbnails.rebuild()
        self._restore_thumbnail_selection(indices)
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
        indices = self._target_page_indices()
        first_idx = min(indices)
        try:
            self.document.delete_pages(indices)
        except PdfError as exc:
            self._error(str(exc))
            return
        self.renderer.invalidate()
        self.thumbnails.rebuild()
        new_idx = min(first_idx, self.document.page_count() - 1)
        self._goto(new_idx)
        self._after_mutation()

    def move_current(self, direction: int) -> None:
        if not self._guard():
            return
        indices = self._target_page_indices()
        try:
            new_indices = self.document.move_pages(indices, direction)
        except PdfError as exc:
            self._error(str(exc))
            return
        if new_indices == indices:
            return
        self.renderer.invalidate()
        self.thumbnails.rebuild()
        self._goto(new_indices[0])
        self._restore_thumbnail_selection(new_indices)
        self._after_mutation()

    def duplicate_current(self) -> None:
        if not self._guard():
            return
        indices = self._target_page_indices()
        new_indices = self.document.duplicate_pages(indices)
        self.renderer.invalidate()
        self.thumbnails.rebuild()
        self._goto(new_indices[0] if new_indices else indices[0])
        self._restore_thumbnail_selection(new_indices)
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

    def merge_pdfs(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Vybrať PDF alebo JPG súbory", "", MERGE_FILTER
        )
        if not paths:
            return

        if self.document.is_open():
            try:
                inserted = self.document.append_files(paths)
            except PdfError as exc:
                self._error(str(exc))
                return
            self.renderer.invalidate()
            self.thumbnails.rebuild()
            self.page_view.refresh()
            self._after_mutation()
            self.status.showMessage(f"Pripojených {inserted} strán.", 4000)
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Uložiť spojené PDF ako", "", PDF_FILTER
        )
        if not out_path:
            return
        if not out_path.lower().endswith(".pdf"):
            out_path += ".pdf"
        try:
            inserted = PdfDocument.merge_files_to_pdf(paths, out_path)
        except PdfError as exc:
            self._error(str(exc))
            return
        self._open_path(out_path)
        self.status.showMessage(f"Spojené do nového PDF: {inserted} strán.", 4000)

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

    def edit_metadata(self) -> None:
        if not self.document.is_open():
            return
        meta = self.document.metadata().get("metadata") or {}
        dlg = MetadataEditDialog(self, metadata=meta)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        self.document.update_metadata(dlg.values())
        self._after_mutation()
        self.status.showMessage("Metadata dokumentu boli upravené.", 4000)

    def text_stamp_dialog(self) -> None:
        if not self.document.is_open():
            return
        selected = self.thumbnails.selected_indices()
        dlg = TextStampDialog(self, has_selection=bool(selected))
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        vals = dlg.values()
        indices = selected if vals["only_selected"] and selected else None
        try:
            if vals["mode"] == "numbers":
                self.document.add_page_numbers(
                    indices=indices,
                    prefix=vals["prefix"],
                    font_size=vals["font_size"],
                )
                message = "Čísla strán boli pridané."
            else:
                self.document.add_text_stamp(
                    vals["text"],
                    indices=indices,
                    font_size=vals["font_size"],
                )
                message = "Text bol pridaný na stránky."
        except PdfError as exc:
            self._error(str(exc))
            return
        self.renderer.invalidate()
        self.thumbnails.rebuild()
        self.page_view.refresh()
        self._after_mutation()
        self.status.showMessage(message, 4000)

    def show_about(self) -> None:
        AboutDialog(self).exec()

    # ================================================================== #
    # Pomocné
    # ================================================================== #
    def _guard(self) -> bool:
        return self.document.is_open()

    def _target_page_indices(self) -> list[int]:
        selected = self.thumbnails.selected_indices()
        if selected:
            return selected
        return [self.page_view.current_index()]

    def _restore_thumbnail_selection(self, indices: list[int]) -> None:
        for idx in indices:
            item = self.thumbnails.item(idx)
            if item is not None:
                item.setSelected(True)

    def _after_mutation(self) -> None:
        self._update_title()
        self._update_status()

    def _update_actions_enabled(self) -> None:
        on = self.document.is_open()
        for act in (
            self.act_save,
            self.act_save_as,
            self.act_save_opt,
            self.act_revert,
            self.act_info,
            self.act_edit_metadata,
            self.act_prev,
            self.act_next,
            self.act_zoom_in,
            self.act_zoom_out,
            self.act_fit_width,
            self.act_fit_page,
            self.act_find,
            self.act_find_next,
            self.act_copy_text,
            self.act_rotate,
            self.act_rotate_all,
            self.act_delete,
            self.act_move_up,
            self.act_move_down,
            self.act_duplicate,
            self.act_insert,
            self.act_extract,
            self.act_export,
            self.act_text_stamp,
        ):
            act.setEnabled(on)
        self.act_merge.setEnabled(True)

    def _update_title(self) -> None:
        base = "LizardPDF"
        if self.document.is_open() and self.document.path:
            name = os.path.basename(self.document.path)
            dirty = " *" if self.document.is_dirty() else ""
            self.setWindowTitle(f"{name}{dirty} — {base}")
            self._doc_label.setText(f"{name}{dirty}")
        else:
            self.setWindowTitle(base)
            self._doc_label.setText("Žiadny dokument")

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
