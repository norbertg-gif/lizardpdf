"""PdfDocument — wrapper nad fitz, drží stav dokumentu v pamäti.

Táto vrstva nepozná Qt. Všetky page-level operácie sa robia
na in-memory ``fitz.Document``; na disk sa zapisuje až pri save().
"""

from __future__ import annotations

import os

import fitz  # PyMuPDF


class PdfError(Exception):
    """Chyba pri práci s PDF (poškodený súbor, zlé heslo, atď.)."""


class PdfDocument:
    def __init__(self) -> None:
        self._doc: fitz.Document | None = None
        self._path: str | None = None
        self._dirty: bool = False

    # ------------------------------------------------------------------ #
    # Otvorenie / zatvorenie
    # ------------------------------------------------------------------ #
    def open(self, path: str, password: str | None = None) -> None:
        """Otvorí PDF. Pri poškodenom/zamknutom súbore vyhodí PdfError."""
        self.close()
        try:
            doc = fitz.open(path)
        except Exception as exc:  # noqa: BLE001 — fitz hádže rôzne typy
            raise PdfError(f"Súbor sa nepodarilo otvoriť: {exc}") from exc

        if doc.needs_pass:
            if password is None or not doc.authenticate(password):
                doc.close()
                raise PdfError("Dokument je chránený heslom.")

        if doc.page_count == 0:
            doc.close()
            raise PdfError("Dokument neobsahuje žiadne stránky.")

        self._doc = doc
        self._path = path
        self._dirty = False

    def close(self) -> None:
        if self._doc is not None:
            self._doc.close()
        self._doc = None
        self._path = None
        self._dirty = False

    # ------------------------------------------------------------------ #
    # Prístup
    # ------------------------------------------------------------------ #
    @property
    def doc(self) -> fitz.Document:
        if self._doc is None:
            raise PdfError("Nie je otvorený žiadny dokument.")
        return self._doc

    @property
    def path(self) -> str | None:
        return self._path

    def is_open(self) -> bool:
        return self._doc is not None

    def page_count(self) -> int:
        return self.doc.page_count

    def get_page(self, idx: int) -> fitz.Page:
        self._check_index(idx)
        return self.doc.load_page(idx)

    def reload(self) -> None:
        """Zahodí neuložené zmeny a znovu otvorí dokument z disku."""
        if not self._path:
            raise PdfError("Dokument ešte nebol uložený na disk.")
        path = self._path
        self.close()
        self.open(path)

    # ------------------------------------------------------------------ #
    # Page operácie
    # ------------------------------------------------------------------ #
    def rotate_page(self, idx: int, delta: int = 90) -> None:
        self._check_index(idx)
        page = self.doc.load_page(idx)
        page.set_rotation((page.rotation + delta) % 360)
        self._mark_dirty()

    def rotate_pages(self, indices: list[int], delta: int = 90) -> None:
        for idx in self._normalize_indices(indices):
            page = self.doc.load_page(idx)
            page.set_rotation((page.rotation + delta) % 360)
        self._mark_dirty()

    def rotate_all(self, delta: int = 90) -> None:
        for page in self.doc:
            page.set_rotation((page.rotation + delta) % 360)
        self._mark_dirty()

    def delete_page(self, idx: int) -> None:
        self._check_index(idx)
        if self.page_count() <= 1:
            raise PdfError("Nedá sa odstrániť posledná stránka dokumentu.")
        self.doc.delete_page(idx)
        self._mark_dirty()

    def delete_pages(self, indices: list[int]) -> None:
        pages = self._normalize_indices(indices)
        if len(pages) >= self.page_count():
            raise PdfError("Nedajú sa odstrániť všetky stránky dokumentu.")
        for idx in sorted(pages, reverse=True):
            self.doc.delete_page(idx)
        self._mark_dirty()

    def move_page(self, src: int, dst: int) -> None:
        self._check_index(src)
        if not 0 <= dst <= self.page_count():
            raise PdfError(f"Neplatná cieľová pozícia: {dst}")
        if src == dst:
            return
        to = -1 if dst >= self.page_count() else dst
        self.doc.move_page(src, to)
        self._mark_dirty()

    def move_pages(self, indices: list[int], direction: int) -> list[int]:
        if direction not in (-1, 1):
            raise PdfError("Neplatný smer posunu stránok.")
        pages = self._normalize_indices(indices)
        order = list(range(self.page_count()))
        selected = set(pages)

        if direction < 0:
            for pos in sorted(pages):
                if pos > 0 and pos - 1 not in selected:
                    order[pos - 1], order[pos] = order[pos], order[pos - 1]
                    selected.remove(pos)
                    selected.add(pos - 1)
        else:
            for pos in sorted(pages, reverse=True):
                if pos < len(order) - 1 and pos + 1 not in selected:
                    order[pos + 1], order[pos] = order[pos], order[pos + 1]
                    selected.remove(pos)
                    selected.add(pos + 1)

        new_pages = sorted(selected)
        if new_pages == pages:
            return pages
        self.doc.select(order)
        self._mark_dirty()
        return new_pages

    def duplicate_page(self, idx: int) -> None:
        self._check_index(idx)
        self.doc.fullcopy_page(idx)
        self._mark_dirty()

    def duplicate_pages(self, indices: list[int]) -> list[int]:
        pages = self._normalize_indices(indices)
        new_indices: list[int] = []
        for idx in pages:
            self.doc.fullcopy_page(idx)
            new_indices.append(self.page_count() - 1)
        self._mark_dirty()
        return new_indices

    def insert_pdf(
        self,
        path: str,
        after_idx: int,
        from_page: int | None = None,
        to_page: int | None = None,
        password: str | None = None,
    ) -> None:
        """Vloží iný PDF za stránku ``after_idx`` (voliteľne len rozsah)."""
        try:
            other = fitz.open(path)
        except Exception as exc:  # noqa: BLE001
            raise PdfError(f"Vkladaný súbor sa nepodarilo otvoriť: {exc}") from exc

        try:
            if other.needs_pass:
                if password is None or not other.authenticate(password):
                    raise PdfError("Vkladaný dokument je chránený heslom.")
            fp = 0 if from_page is None else from_page
            tp = other.page_count - 1 if to_page is None else to_page
            self.doc.insert_pdf(
                other,
                from_page=fp,
                to_page=tp,
                start_at=after_idx + 1,
            )
        finally:
            other.close()
        self._mark_dirty()

    def append_pdfs(self, paths: list[str]) -> int:
        """Pripojí viac PDF na koniec aktuálneho dokumentu. Vracia počet strán."""
        if not paths:
            raise PdfError("Nie sú vybrané žiadne PDF súbory na spojenie.")

        inserted = 0
        for path in paths:
            try:
                other = fitz.open(path)
            except Exception as exc:  # noqa: BLE001
                raise PdfError(f"Súbor sa nepodarilo otvoriť: {path}: {exc}") from exc

            try:
                if other.needs_pass:
                    raise PdfError(f"Dokument je chránený heslom: {path}")
                if other.page_count == 0:
                    continue
                self.doc.insert_pdf(other, start_at=self.page_count())
                inserted += other.page_count
            finally:
                other.close()

        if inserted:
            self._mark_dirty()
        return inserted

    def extract_pages(self, indices: list[int], out_path: str) -> None:
        """Vyextrahuje vybrané stránky do nového PDF (v poradí ``indices``)."""
        if not indices:
            raise PdfError("Nie sú vybrané žiadne stránky na extrakciu.")
        for idx in indices:
            self._check_index(idx)
        new = fitz.open()
        try:
            for idx in indices:
                new.insert_pdf(self.doc, from_page=idx, to_page=idx)
            new.save(out_path, garbage=4, deflate=True)
        finally:
            new.close()

    def page_text(self, idx: int) -> str:
        self._check_index(idx)
        return self.doc.load_page(idx).get_text("text")

    def has_text(self) -> bool:
        return any(self.page_text(idx).strip() for idx in range(self.page_count()))

    def search_matches(self, idx: int, query: str):
        self._check_index(idx)
        query = query.strip()
        if not query:
            return []
        return self.doc.load_page(idx).search_for(query)

    def search_text(self, query: str, start_idx: int = 0) -> int | None:
        query = query.strip()
        if not query:
            raise PdfError("Zadajte text na hľadanie.")
        count = self.page_count()
        if count == 0:
            return None
        start_idx %= count
        order = list(range(start_idx, count)) + list(range(0, start_idx))
        needle = query.casefold()
        for idx in order:
            page = self.doc.load_page(idx)
            if self.search_matches(idx, query):
                return idx
            if needle in page.get_text("text").casefold():
                return idx
        return None

    def add_text_stamp(
        self,
        text: str,
        indices: list[int] | None = None,
        font_size: int = 10,
        bottom_margin: float = 24,
    ) -> None:
        text = text.strip()
        if not text:
            raise PdfError("Zadajte text pečiatky.")
        pages = self._normalize_indices(indices)
        for idx in pages:
            page = self.doc.load_page(idx)
            rect = page.rect
            point = fitz.Point(36, max(12, rect.height - bottom_margin))
            page.insert_text(
                point,
                text,
                fontsize=font_size,
                color=(0.35, 0.35, 0.35),
                overlay=True,
            )
        self._mark_dirty()

    def add_page_numbers(
        self,
        indices: list[int] | None = None,
        prefix: str = "Strana",
        font_size: int = 10,
        bottom_margin: float = 24,
    ) -> None:
        pages = self._normalize_indices(indices)
        total = self.page_count()
        for idx in pages:
            page = self.doc.load_page(idx)
            rect = page.rect
            text = f"{prefix} {idx + 1} / {total}".strip()
            text_width = fitz.get_text_length(text, fontsize=font_size)
            x = max(36, (rect.width - text_width) / 2)
            y = max(12, rect.height - bottom_margin)
            page.insert_text(
                fitz.Point(x, y),
                text,
                fontsize=font_size,
                color=(0.35, 0.35, 0.35),
                overlay=True,
            )
        self._mark_dirty()

    # ------------------------------------------------------------------ #
    # Metadata / stav
    # ------------------------------------------------------------------ #
    def metadata(self) -> dict:
        doc = self.doc
        sizes = []
        for page in doc:
            rect = page.rect
            sizes.append((round(rect.width, 1), round(rect.height, 1)))

        file_size = None
        if self._path and os.path.exists(self._path):
            file_size = os.path.getsize(self._path)

        return {
            "path": self._path,
            "page_count": doc.page_count,
            "page_sizes": sizes,
            "file_size": file_size,
            "metadata": dict(doc.metadata or {}),
        }

    def update_metadata(self, values: dict[str, str]) -> None:
        meta = dict(self.doc.metadata or {})
        allowed = {
            "title",
            "author",
            "subject",
            "keywords",
            "creator",
            "producer",
        }
        for key in allowed:
            if key in values:
                meta[key] = values[key].strip()
        self.doc.set_metadata(meta)
        self._mark_dirty()

    def is_dirty(self) -> bool:
        return self._dirty

    # ------------------------------------------------------------------ #
    # Ukladanie
    # ------------------------------------------------------------------ #
    def save(self, path: str, optimize: bool = False) -> None:
        doc = self.doc
        same_file = self._path is not None and os.path.abspath(path) == os.path.abspath(self._path)

        try:
            if optimize:
                if same_file:
                    self._save_via_temp(path, garbage=4, deflate=True)
                else:
                    doc.save(path, garbage=4, deflate=True)
            else:
                if same_file:
                    doc.save(path, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
                else:
                    doc.save(path)
        except Exception as exc:  # noqa: BLE001
            raise PdfError(f"Uloženie zlyhalo: {exc}") from exc

        self._path = path
        self._dirty = False

    def _save_via_temp(self, path: str, **opts) -> None:
        tmp = path + ".tmp_save"
        self.doc.save(tmp, **opts)
        self.doc.close()
        os.replace(tmp, path)
        self._doc = fitz.open(path)

    # ------------------------------------------------------------------ #
    # Pomocné
    # ------------------------------------------------------------------ #
    def _check_index(self, idx: int) -> None:
        if not 0 <= idx < self.page_count():
            raise PdfError(f"Neplatný index stránky: {idx}")

    def _normalize_indices(self, indices: list[int] | None) -> list[int]:
        if indices is None:
            return list(range(self.page_count()))
        if not indices:
            raise PdfError("Nie sú vybrané žiadne stránky.")
        pages = sorted(set(indices))
        for idx in pages:
            self._check_index(idx)
        return pages

    def _mark_dirty(self) -> None:
        self._dirty = True
