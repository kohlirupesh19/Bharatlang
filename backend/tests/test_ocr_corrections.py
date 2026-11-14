"""Manifest-declared OCR corrections: verified fixes applied at load time, never silently."""
import pytest

from backend.app.services.rag.corpus.corrections import (
    CorrectionError,
    OcrCorrection,
    apply_corrections,
    parse_corrections,
)
from backend.app.services.rag.corpus.ocr_blocks import Block

RICE_ROW = ["१", "भात (तांदूळ)", "७०", "६९०००", "०.७५", "४५७.५०"]
HEADER = ["अ.क्र.", "पीक", "जोखीमस्तर", "विमा संरक्षित रक्कम", "दर", "हप्ता"]


def _table_block(page: int = 46) -> Block:
    return Block(page, "table", "", (HEADER, [RICE_ROW, ["२", "नाचणी", "७०", "३५०००", "०.२५", "८७.५०"]]))


def _fix(page: int = 46, find: str = "६९०००", replace: str = "६१०००") -> OcrCorrection:
    return OcrCorrection(page=page, find=find, replace=replace, evidence="PDF p46 render")


def test_parse_corrections_reads_manifest_entries():
    doc = {"doc_id": "d", "ocr_corrections": [
        {"page": 46, "find": "६९०००", "replace": "६१०००", "evidence": "PDF p46 render"}]}
    assert parse_corrections(doc) == (_fix(),)


def test_parse_corrections_absent_is_empty():
    assert parse_corrections({"doc_id": "d"}) == ()


@pytest.mark.parametrize("bad", [
    {"page": 46, "find": "", "replace": "x", "evidence": "e"},
    {"page": 46, "find": "a", "replace": "a", "evidence": "e"},
    {"page": 46, "find": "a", "replace": "b", "evidence": ""},
    {"page": "46", "find": "a", "replace": "b", "evidence": "e"},
])
def test_parse_corrections_rejects_invalid_entries(bad):
    with pytest.raises(CorrectionError):
        parse_corrections({"doc_id": "d", "ocr_corrections": [bad]})


def test_correction_fixes_table_cell_without_mutating_input():
    original = _table_block()
    fixed = apply_corrections([original], (_fix(),), "d")
    assert fixed[0].table[1][0][3] == "६१०००"
    assert original.table[1][0][3] == "६९०००"
    assert fixed[0].table[1][1] == original.table[1][1]


def test_correction_fixes_text_block():
    block = Block(3, "text", "रक्कम रु. ६९००० प्रति हे.", None)
    fixed = apply_corrections([block], (_fix(page=3),), "d")
    assert fixed[0].text == "रक्कम रु. ६१००० प्रति हे."


def test_correction_only_touches_its_page():
    other_page = _table_block(page=47)
    target = _table_block(page=46)
    fixed = apply_corrections([other_page, target], (_fix(),), "d")
    assert fixed[0].table[1][0][3] == "६९०००"
    assert fixed[1].table[1][0][3] == "६१०००"


def test_correction_that_no_longer_matches_fails_loudly():
    with pytest.raises(CorrectionError, match="matched 0"):
        apply_corrections([_table_block()], (_fix(find="७७७७७"),), "d")


def test_ambiguous_correction_fails_loudly():
    block = Block(46, "text", "६९००० आणि ६९०००", None)
    with pytest.raises(CorrectionError, match="matched 2"):
        apply_corrections([block], (_fix(),), "d")


def test_no_corrections_returns_blocks_unchanged():
    blocks = [_table_block()]
    assert apply_corrections(blocks, (), "d") == blocks
