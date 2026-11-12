"""HTML table -> (context lines, column names, data rows), honouring rowspan/colspan.

Government GR tables carry full-width title rows, a caption row (district, insurer, ...),
multi-level headers built from rowspan/colspan, and a "1 2 3 ... N" column-number row.
The table is expanded into a grid so each value lines up with its real column, and
every column gets its full name ("parent › child"). Title and caption rows become
context lines that the chunker repeats in each chunk of the table.
"""
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple

Table = Tuple[List[str], List[List[str]]]
HEADER_SEP = " › "
_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


@dataclass(frozen=True)
class _Cell:
    text: str
    is_th: bool
    rowspan: int
    colspan: int


@dataclass(frozen=True)
class _Slot:
    cell: _Cell
    origin: Tuple[int, int]  # (row, col) where the cell starts


def _span(attrs, name: str) -> int:
    value = dict(attrs).get(name) or "1"
    return int(value) if value.isdigit() and int(value) > 0 else 1


class _RowCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: List[List[_Cell]] = []
        self._row: Optional[List[_Cell]] = None
        self._buf: Optional[List[str]] = None
        self._attrs: Tuple[bool, int, int] = (False, 1, 1)

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._buf = []
            self._attrs = (tag == "th", _span(attrs, "rowspan"), _span(attrs, "colspan"))
        elif tag == "br" and self._buf is not None:
            self._buf.append(" ")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._buf is not None and self._row is not None:
            is_th, rowspan, colspan = self._attrs
            self._row.append(_Cell(" ".join("".join(self._buf).split()), is_th, rowspan, colspan))
            self._buf = None
        elif tag == "tr" and self._row is not None:
            if any(c.text for c in self._row):
                self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._buf is not None:
            self._buf.append(data)


def _expand(rows: List[List[_Cell]]) -> List[List[Optional[_Slot]]]:
    occupied: Dict[Tuple[int, int], _Slot] = {}
    for r, row in enumerate(rows):
        c = 0
        for cell in row:
            while (r, c) in occupied:
                c += 1
            for dr in range(cell.rowspan):
                for dc in range(cell.colspan):
                    occupied[(r + dr, c + dc)] = _Slot(cell, (r, c))
            c += cell.colspan
    grid = [[occupied.get((r, c)) for c in range(max((c for (_r, c) in occupied), default=-1) + 1)]
            for r in range(len(rows))]
    width = _body_width(grid)
    return [row[:width] for row in grid]


def _body_width(grid: List[List[Optional[_Slot]]]) -> int:
    """OCR often inflates title/caption colspans past the real table; trust the body rows' width.

    Body rows are rows with 3+ distinct cells; the most common occupied width among them wins
    (ties go to the wider). Falls back to the full grid width for small or irregular tables.
    """
    widths = [sum(1 for slot in row if slot is not None) for row in grid if len(_origins(row)) >= 3]
    if not widths:
        return len(grid[0]) if grid else 0
    counts: Dict[int, int] = {}
    for w in widths:
        counts[w] = counts.get(w, 0) + 1
    return max(counts, key=lambda w: (counts[w], w))


def _origins(grid_row: List[Optional[_Slot]]) -> List[Tuple[int, int]]:
    seen: List[Tuple[int, int]] = []
    for slot in grid_row:
        if slot is not None and slot.origin not in seen:
            seen.append(slot.origin)
    return seen


def _is_full_width(r: int, grid_row: List[Optional[_Slot]]) -> bool:
    origins = _origins(grid_row)
    return len(grid_row) > 1 and len(origins) == 1 and origins[0][0] == r and None not in grid_row


def _is_header(grid_row: List[Optional[_Slot]]) -> bool:
    return all(slot is not None and slot.cell.is_th for slot in grid_row)


def _is_data(grid_row: List[Optional[_Slot]]) -> bool:
    width = len(grid_row)
    has_td = any(slot is not None and not slot.cell.is_th for slot in grid_row)
    return has_td and len(_origins(grid_row)) >= max(2, (width + 1) // 2)


def _row_texts(r: int, grid_row: List[Optional[_Slot]]) -> List[str]:
    """One value per column; a colspan'd cell is written once, a rowspan'd cell repeats."""
    texts = []
    for c, slot in enumerate(grid_row):
        texts.append(slot.cell.text if slot is not None and (slot.origin[1] == c) else "")
    return texts


def _is_column_number_row(texts: List[str]) -> bool:
    return len(texts) >= 3 and [t.translate(_DEVANAGARI_DIGITS) for t in texts] == [str(i) for i in range(1, len(texts) + 1)]


def _column_names(grid: List[List[Optional[_Slot]]], header_rows: List[int], width: int) -> List[str]:
    names = []
    for c in range(width):
        levels: List[str] = []
        last_origin = None
        for r in header_rows:
            slot = grid[r][c]
            if slot is None or slot.origin == last_origin:
                continue
            last_origin = slot.origin
            if slot.cell.text and (not levels or levels[-1] != slot.cell.text):
                levels.append(slot.cell.text)
        names.append(HEADER_SEP.join(levels))
    return names


def parse_table_with_context(html: str) -> Tuple[Tuple[str, ...], Table]:
    collector = _RowCollector()
    collector.feed(html)
    if not collector.rows:
        return (), ([], [])
    grid = _expand(collector.rows)
    width = len(grid[0])
    first_data = next((r for r, row in enumerate(grid) if _is_data(row) and not _is_header(row)), len(grid))

    header_rows = [r for r in range(first_data) if _is_header(grid[r]) and not _is_full_width(r, grid[r])]
    body_start = header_rows[-1] + 1 if header_rows else first_data
    # Rows above the column headers (titles, district/insurer captions) describe the whole table.
    context = [line for line in (" | ".join(c.text for c in collector.rows[r] if c.text)
                                 for r in range(body_start) if r not in header_rows) if line]

    data: List[List[str]] = []
    for r in range(body_start, len(grid)):
        row = grid[r]
        if _is_full_width(r, row):
            data.append([row[0].cell.text])
            continue
        texts = _row_texts(r, row)
        if not any(texts) or _is_column_number_row(texts):
            continue
        data.append(texts)

    if header_rows:
        header = _column_names(grid, header_rows, width)
    elif data and len(data[0]) == width:
        header, data = data[0], data[1:]  # no <th>: first row is the header
    else:
        header = []
    return tuple(context), (header, data)


def parse_table(html: str) -> Table:
    return parse_table_with_context(html)[1]
