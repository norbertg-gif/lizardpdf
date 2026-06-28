"""Testy core logiky PdfDocument — bez Qt, čisto na fitz."""

from __future__ import annotations

import fitz
import pytest

from pdf_tool.core.document import PdfDocument, PdfError


def _make_pdf(path, pages: int = 3) -> None:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Strana {i + 1}")
    doc.save(str(path))
    doc.close()


def _make_jpg(path) -> None:
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 80, 60), False)
    pix.clear_with(230)
    pix.save(str(path))


@pytest.fixture()
def sample(tmp_path):
    p = tmp_path / "sample.pdf"
    _make_pdf(p, 3)
    d = PdfDocument()
    d.open(str(p))
    yield d
    d.close()


def test_open_and_count(sample):
    assert sample.page_count() == 3
    assert sample.is_open()
    assert not sample.is_dirty()


def test_open_missing(tmp_path):
    d = PdfDocument()
    with pytest.raises(PdfError):
        d.open(str(tmp_path / "nope.pdf"))


def test_rotate_sets_dirty(sample):
    sample.rotate_page(0, 90)
    assert sample.get_page(0).rotation == 90
    assert sample.is_dirty()


def test_rotate_all(sample):
    sample.rotate_all(90)
    for page in sample.doc:
        assert page.rotation == 90


def test_rotate_pages(sample):
    sample.rotate_pages([0, 2], 90)
    assert sample.get_page(0).rotation == 90
    assert sample.get_page(1).rotation == 0
    assert sample.get_page(2).rotation == 90


def test_delete_page(sample):
    sample.delete_page(1)
    assert sample.page_count() == 2


def test_delete_pages(sample):
    sample.delete_pages([0, 2])
    assert sample.page_count() == 1
    assert "Strana 2" in sample.page_text(0)


def test_delete_all_pages_blocked(sample):
    with pytest.raises(PdfError):
        sample.delete_pages([0, 1, 2])


def test_delete_last_remaining_blocked(tmp_path):
    p = tmp_path / "one.pdf"
    _make_pdf(p, 1)
    d = PdfDocument()
    d.open(str(p))
    with pytest.raises(PdfError):
        d.delete_page(0)
    d.close()


def test_move_page(sample):
    # presuň stranu 0 na koniec
    sample.move_page(0, 3)
    assert sample.page_count() == 3


def test_move_pages_up(sample):
    moved = sample.move_pages([1, 2], -1)
    assert moved == [0, 1]
    assert "Strana 2" in sample.page_text(0)
    assert "Strana 3" in sample.page_text(1)
    assert "Strana 1" in sample.page_text(2)


def test_move_pages_down(sample):
    moved = sample.move_pages([0, 1], 1)
    assert moved == [1, 2]
    assert "Strana 3" in sample.page_text(0)
    assert "Strana 1" in sample.page_text(1)
    assert "Strana 2" in sample.page_text(2)


def test_duplicate_page(sample):
    sample.duplicate_page(0)
    assert sample.page_count() == 4


def test_duplicate_pages(sample):
    new_indices = sample.duplicate_pages([0, 2])
    assert new_indices == [3, 4]
    assert sample.page_count() == 5
    assert "Strana 1" in sample.page_text(3)
    assert "Strana 3" in sample.page_text(4)


def test_insert_pdf(sample, tmp_path):
    other = tmp_path / "other.pdf"
    _make_pdf(other, 2)
    sample.insert_pdf(str(other), after_idx=0)
    assert sample.page_count() == 5


def test_insert_pdf_range(sample, tmp_path):
    other = tmp_path / "other.pdf"
    _make_pdf(other, 5)
    sample.insert_pdf(str(other), after_idx=0, from_page=1, to_page=2)
    assert sample.page_count() == 5  # 3 + 2


def test_append_pdfs(sample, tmp_path):
    one = tmp_path / "one.pdf"
    two = tmp_path / "two.pdf"
    _make_pdf(one, 2)
    _make_pdf(two, 1)
    inserted = sample.append_pdfs([str(one), str(two)])
    assert inserted == 3
    assert sample.page_count() == 6
    assert sample.is_dirty()


def test_append_files_accepts_jpg(sample, tmp_path):
    image = tmp_path / "image.jpg"
    _make_jpg(image)
    inserted = sample.append_files([str(image)])
    assert inserted == 1
    assert sample.page_count() == 4
    assert sample.is_dirty()


def test_merge_files_to_pdf_without_open_document(tmp_path):
    pdf = tmp_path / "one.pdf"
    image = tmp_path / "image.jpg"
    out = tmp_path / "merged.pdf"
    _make_pdf(pdf, 2)
    _make_jpg(image)

    inserted = PdfDocument.merge_files_to_pdf([str(pdf), str(image)], str(out))

    assert inserted == 3
    chk = fitz.open(str(out))
    assert chk.page_count == 3
    chk.close()


def test_extract_pages(sample, tmp_path):
    out = tmp_path / "extract.pdf"
    sample.extract_pages([0, 2], str(out))
    chk = fitz.open(str(out))
    assert chk.page_count == 2
    chk.close()


def test_extract_empty_raises(sample, tmp_path):
    with pytest.raises(PdfError):
        sample.extract_pages([], str(tmp_path / "x.pdf"))


def test_metadata(sample):
    meta = sample.metadata()
    assert meta["page_count"] == 3
    assert len(meta["page_sizes"]) == 3


def test_update_metadata(sample):
    sample.update_metadata({"title": "Novy nazov", "author": "Tester"})
    meta = sample.metadata()["metadata"]
    assert meta["title"] == "Novy nazov"
    assert meta["author"] == "Tester"
    assert sample.is_dirty()


def test_page_text_and_search(sample):
    assert sample.has_text()
    assert "Strana 2" in sample.page_text(1)
    assert sample.search_matches(1, "Strana")
    assert sample.search_text("strana 3") == 2
    assert sample.search_text("strana 1", start_idx=1) == 0
    assert sample.search_text("nenajde-sa") is None


def test_text_stamp_selected_pages(sample):
    sample.add_text_stamp("Kopia", indices=[1])
    assert "Kopia" not in sample.page_text(0)
    assert "Kopia" in sample.page_text(1)
    assert sample.is_dirty()


def test_page_numbers(sample):
    sample.add_page_numbers()
    assert "Strana 1 / 3" in sample.page_text(0)
    assert "Strana 3 / 3" in sample.page_text(2)
    assert sample.is_dirty()


def test_image_only_pdf_has_no_text(tmp_path):
    text_pdf = tmp_path / "text.pdf"
    image_pdf = tmp_path / "image.pdf"
    _make_pdf(text_pdf, 1)

    src = fitz.open(str(text_pdf))
    pix = src[0].get_pixmap(dpi=120)
    png = tmp_path / "page.png"
    pix.save(str(png))
    src.close()

    doc = fitz.open()
    page = doc.new_page()
    page.insert_image(page.rect, filename=str(png))
    doc.save(str(image_pdf))
    doc.close()

    pdf = PdfDocument()
    pdf.open(str(image_pdf))
    assert not pdf.has_text()
    assert pdf.search_text("Strana") is None
    pdf.close()


def test_save_as_clears_dirty(sample, tmp_path):
    sample.rotate_page(0, 90)
    assert sample.is_dirty()
    out = tmp_path / "saved.pdf"
    sample.save(str(out))
    assert not sample.is_dirty()
    # rotácia sa zapísala
    chk = fitz.open(str(out))
    assert chk.load_page(0).rotation == 90
    chk.close()


def test_save_optimize_same_file(sample):
    path = sample.path
    sample.rotate_page(0, 90)
    sample.save(path, optimize=True)
    assert not sample.is_dirty()
    assert sample.page_count() == 3
    assert sample.get_page(0).rotation == 90


def test_reload_reverts_unsaved_changes(sample):
    sample.delete_page(1)
    assert sample.page_count() == 2
    sample.reload()
    assert sample.page_count() == 3
    assert not sample.is_dirty()


def test_bad_index(sample):
    with pytest.raises(PdfError):
        sample.rotate_page(99)
