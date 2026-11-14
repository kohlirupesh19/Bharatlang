"""Parse Surya OCR results (HTML blocks with layout labels) into typed blocks."""
import json
from dataclasses import dataclass, replace
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from backend.app.services.rag.corpus.table_grid import Table, parse_table, parse_table_with_context

__all__ = ["Block", "Table", "parse_table", "parse_table_with_context", "html_to_text",
           "blocks_from_surya_page", "blocks_from_surya_results", "remap_to_pdf_pages"]

# Repeated on every page (GR number, "पृष्ठ ४ पैकी २") or non-text; never useful as evidence.
_DROPPED_LABELS = {"PageHeader", "PageFooter", "Picture", "Figure"}
_HEADING_LABELS = {"SectionHeader", "Title"}
_BLOCK_TAGS = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "ol", "ul", "table"}


@dataclass(frozen=True)
class Block:
    page: int
    kind: str  # "heading" | "text" | "table"
    text: str
    table: Optional[Table]
    # Table title/caption lines (e.g. "जिल्हा : रत्नागिरी") repeated in every chunk of the table.
    context: Tuple[str, ...] = ()


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "br" or tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")
        elif tag in ("td", "th"):
            self.parts.append(" ")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    lines = (" ".join(line.split()) for line in "".join(parser.parts).split("\n"))
    return "\n".join(line for line in lines if line)


_CAPTION_MAX_CHARS = 150  # a caption line (district, form no., season); longer text is prose
_CAPTION_MAX_LINES = 8


def _is_caption_line(block: Block) -> bool:
    """Short heading, or a short label line ("जिल्हा : धुळे"); a sentence ending in । or . is prose."""
    text = block.text.strip()
    if block.kind == "heading":
        return len(text) <= _CAPTION_MAX_CHARS
    if block.kind != "text" or len(text) > _CAPTION_MAX_CHARS:
        return False
    return ":" in text or not text.endswith(("।", "."))


def _attach_split_captions(blocks: List[Block]) -> List[Block]:
    """Surya sometimes emits a table's caption as headings/short text blocks above a bare table.

    For a table with no caption of its own, the run of short blocks directly above it becomes
    its context. Caption text blocks are folded into the table; headings also stay in the
    stream because they still set the running section for what follows.
    """
    result: List[Block] = []
    for block in blocks:
        if block.kind != "table" or block.context:
            result.append(block)
            continue
        start = len(result)
        while start > 0 and len(result) - start < _CAPTION_MAX_LINES and _is_caption_line(result[start - 1]):
            start -= 1
        caption = result[start:]
        if caption:
            result = result[:start] + [b for b in caption if b.kind == "heading"]
        result.append(replace(block, context=tuple(b.text for b in caption)))
    return result


def blocks_from_surya_page(page: dict) -> List[Block]:
    page_no = int(page.get("page", 0))
    blocks: List[Block] = []
    for raw in sorted(page.get("blocks", []), key=lambda b: b.get("reading_order", 0)):
        label = raw.get("label", "")
        html = raw.get("html") or ""
        if label in _DROPPED_LABELS or raw.get("skipped") or not html.strip():
            continue
        if label == "Table":
            context, table = parse_table_with_context(html)
            if table[1] or table[0]:
                blocks.append(Block(page_no, "table", "", table, context))
            continue
        text = html_to_text(html)
        if text:
            blocks.append(Block(page_no, "heading" if label in _HEADING_LABELS else "text", text, None))
    return _attach_split_captions(blocks)


def _pdf_pages_from_spec(spec: str) -> List[int]:
    """Surya page_range syntax ("0-109,367-368", 0-based inclusive) -> 1-based PDF pages in order."""
    pages: List[int] = []
    for part in spec.split(","):
        lo, sep, hi = part.strip().partition("-")
        if not lo.isdigit() or (sep and not hi.isdigit()):
            raise ValueError(f"Malformed OCR page range {spec!r}")
        start, end = int(lo), int(hi) if sep else int(lo)
        if end < start:
            raise ValueError(f"Malformed OCR page range {spec!r}")
        pages.extend(range(start + 1, end + 2))
    return pages


def remap_to_pdf_pages(blocks: Sequence[Block], ocr_pages: Optional[str]) -> List[Block]:
    """Surya numbers the pages it processed 1..N; map them back to real PDF page numbers."""
    if ocr_pages is None:
        return list(blocks)
    pdf_pages = _pdf_pages_from_spec(ocr_pages)
    remapped: List[Block] = []
    for block in blocks:
        if not 1 <= block.page <= len(pdf_pages):
            raise ValueError(f"OCR result page {block.page} is outside the declared ranges {ocr_pages!r}")
        remapped.append(replace(block, page=pdf_pages[block.page - 1]))
    return remapped


def blocks_from_surya_results(results_path: Path) -> List[Block]:
    """results.json maps one PDF stem to its list of pages."""
    data = json.loads(Path(results_path).read_text(encoding="utf-8"))
    pages: Iterable[dict] = next(iter(data.values()))
    return [block for page in pages for block in blocks_from_surya_page(page)]
