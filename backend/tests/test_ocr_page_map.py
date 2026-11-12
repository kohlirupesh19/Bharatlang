"""Surya numbers processed pages 1..N; citations must use the real PDF page numbers."""
import pytest

from backend.app.services.rag.corpus.ocr_blocks import Block, remap_to_pdf_pages


def _blocks(*pages: int):
    return [Block(p, "text", f"p{p}", None) for p in pages]


def test_full_document_ocr_keeps_page_numbers():
    assert [b.page for b in remap_to_pdf_pages(_blocks(1, 2, 3), None)] == [1, 2, 3]


def test_partial_ranges_map_to_pdf_pages():
    # Surya page_range "0-1,367-368" (0-based) -> results pages 1..4 -> PDF pages 1, 2, 368, 369
    remapped = remap_to_pdf_pages(_blocks(1, 2, 3, 4), "0-1,367-368")
    assert [b.page for b in remapped] == [1, 2, 368, 369]
    assert [b.text for b in remapped] == ["p1", "p2", "p3", "p4"]


def test_single_page_ranges():
    assert [b.page for b in remap_to_pdf_pages(_blocks(1, 2), "4,9")] == [5, 10]


def test_input_blocks_not_mutated():
    original = _blocks(3)
    remap_to_pdf_pages(original, "0-1,367-368")
    assert original[0].page == 3


def test_result_page_outside_declared_ranges_fails():
    with pytest.raises(ValueError, match="page 5"):
        remap_to_pdf_pages(_blocks(5), "0-1,367-368")


@pytest.mark.parametrize("spec", ["", "a-b", "5-2", "-1"])
def test_malformed_page_spec_fails(spec):
    with pytest.raises(ValueError):
        remap_to_pdf_pages(_blocks(1), spec)
