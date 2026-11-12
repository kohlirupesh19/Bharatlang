"""Section- and table-aware chunking.

Every chunk starts with "<document title>\\n<section heading>" so it is self-describing when
retrieved alone. Table rows are rendered as "column: value; ..." lines, so a row never loses
its headers, and a large table is split between rows, never inside one.
"""
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from backend.app.services.rag.chunking import split_into_units
from backend.app.services.rag.corpus.ocr_blocks import Block
from backend.app.services.rag.corpus.table_grid import HEADER_SEP

MIN_BODY_CHARS = 120


@dataclass(frozen=True)
class DocMeta:
    doc_id: str
    title: str
    scheme: str
    gr_number: Optional[str]
    issue_date: Optional[str]
    status: str
    source_url: str
    language: str
    superseded_by: Tuple[str, ...]
    issuing_authority: str


def render_row(header: Sequence[str], row: Sequence[str]) -> str:
    """"col: value; parent: child v, child v" — sub-columns are grouped under their parent once."""
    if len(row) == 1 and len(header) > 1:
        return row[0]  # full-width label row inside the table body (e.g. a season or group name)
    parts: List[str] = []
    group: Optional[str] = None
    members: List[str] = []
    for i, value in enumerate(row):
        if not value:
            continue
        name = header[i] if i < len(header) and header[i] else ""
        parent, sep, leaf = name.partition(HEADER_SEP)
        if sep and parent == group:
            members.append(f"{leaf} {value}")
            continue
        if group is not None:
            parts.append(f"{group}: {', '.join(members)}")
        group, members = (parent, [f"{leaf} {value}"]) if sep else (None, [])
        if not sep:
            parts.append(f"{name}: {value}" if name else value)
    if group is not None:
        parts.append(f"{group}: {', '.join(members)}")
    return "; ".join(parts)


class _Builder:
    def __init__(self, meta: DocMeta, max_chars: int) -> None:
        self.meta, self.max_chars = meta, max_chars
        self.chunks: List[Dict[str, object]] = []
        self.section = ""

    def prefix(self) -> str:
        section = self.section
        room = self.max_chars - MIN_BODY_CHARS - len(self.meta.title) - 2
        if len(section) > room:
            section = section[: max(room, 0)].rstrip()
        return f"{self.meta.title}\n{section}\n" if section else f"{self.meta.title}\n"

    def body_budget(self) -> int:
        return self.max_chars - len(self.prefix())

    def emit(self, body: str, page: int, chunk_type: str) -> None:
        meta = asdict(self.meta)
        meta["superseded_by"] = list(self.meta.superseded_by)
        self.chunks.append({
            **meta,
            "text": self.prefix() + body,
            "chunk_id": f"{self.meta.doc_id}:p{page}:c{len(self.chunks)}",
            "page": page,
            "section": self.section,
            "chunk_type": chunk_type,
        })

    def pack(self, units: List[str], page: int, chunk_type: str, joiner: str) -> None:
        budget, current = self.body_budget(), ""
        for unit in units:
            candidate = f"{current}{joiner}{unit}" if current else unit
            if len(candidate) <= budget:
                current = candidate
                continue
            if current:
                self.emit(current, page, chunk_type)
            current = unit
        if current:
            self.emit(current, page, chunk_type)


def chunk_blocks(blocks: Sequence[Block], meta: DocMeta, max_chars: int = 900) -> List[Dict[str, object]]:
    builder = _Builder(meta, max_chars)
    pending: List[str] = []
    pending_page: Optional[int] = None

    def flush_text() -> None:
        nonlocal pending, pending_page
        if pending and pending_page is not None:
            units = [u for text in pending for u, _ in split_into_units(text, builder.body_budget())]
            builder.pack(units, pending_page, "text", "\n")
        pending, pending_page = [], None

    for block in blocks:
        if block.kind == "heading":
            flush_text()
            builder.section = " ".join(block.text.split())
        elif block.kind == "table" and block.table is not None:
            flush_text()
            header, rows = block.table
            enclosing_section = builder.section
            if block.context:
                # A captioned table (title, district, insurer) is its own section; the running
                # heading may be stale (e.g. a form heading from an earlier page).
                builder.section = " | ".join(block.context)
            lines = [render_row(header, row) for row in rows] or [render_row([], header)]
            budget = builder.body_budget()
            lines = [u for line in lines for u, _ in split_into_units(line, budget)]
            builder.pack(lines, block.page, "table", "\n")
            builder.section = enclosing_section
        else:
            if pending_page is not None and block.page != pending_page:
                flush_text()  # keep each chunk's citation page accurate
            pending_page = block.page if pending_page is None else pending_page
            pending.append(block.text)
    flush_text()
    return builder.chunks
