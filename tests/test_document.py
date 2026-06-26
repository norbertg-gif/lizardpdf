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


def test_delete_page(sample):
    sample.delete_page(1)
    assert sample.page_count() == 2


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


def test_duplicate_page(sample):
    sample.duplicate_page(0)
    assert sample.page_count() == 4


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


def test_bad_index(sample):
    with pytest.raises(PdfError):
        sample.rotate_page(99)
