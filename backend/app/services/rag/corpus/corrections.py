"""Manifest-declared OCR corrections.

A correction is a human-verified fix (find -> replace) on one page of one document,
recorded in manifest.json under the document's "ocr_corrections" with the evidence
used to verify it. Raw OCR output is never edited. Each correction must match exactly
once on its page; anything else fails the build so a stale or ambiguous fix (for
example after re-running OCR) is noticed instead of silently ignored.
"""
from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Sequence, Tuple

from backend.app.services.rag.corpus.ocr_blocks import Block, Table


class CorrectionError(ValueError):
    pass


@dataclass(frozen=True)
class OcrCorrection:
    page: int
    find: str
    replace: str
    evidence: str


def parse_corrections(doc: Dict) -> Tuple[OcrCorrection, ...]:
    parsed = []
    for i, raw in enumerate(doc.get("ocr_corrections", [])):
        where = f"{doc.get('doc_id')}: ocr_corrections[{i}]"
        page, find, repl, evidence = (raw.get(k) for k in ("page", "find", "replace", "evidence"))
        if not isinstance(page, int) or page < 1:
            raise CorrectionError(f"{where}: 'page' must be a positive int (Surya 1-based page)")
        if not isinstance(find, str) or not find or not isinstance(repl, str) or find == repl:
            raise CorrectionError(f"{where}: 'find' must be non-empty and differ from 'replace'")
        if not isinstance(evidence, str) or not evidence.strip():
            raise CorrectionError(f"{where}: 'evidence' is required (how the fix was verified)")
        parsed.append(OcrCorrection(page, find, repl, evidence))
    return tuple(parsed)


def _count(block: Block, find: str) -> int:
    in_context = sum(line.count(find) for line in block.context)
    if block.table is None:
        return block.text.count(find) + in_context
    header, rows = block.table
    return in_context + sum(cell.count(find) for cell in [*header, *(c for row in rows for c in row)])


def _fix_table(table: Table, find: str, repl: str) -> Table:
    header, rows = table
    return ([c.replace(find, repl) for c in header],
            [[c.replace(find, repl) for c in row] for row in rows])


def _apply_one(block: Block, fix: OcrCorrection) -> Block:
    context = tuple(line.replace(fix.find, fix.replace) for line in block.context)
    if block.table is not None:
        return replace(block, table=_fix_table(block.table, fix.find, fix.replace), context=context)
    return replace(block, text=block.text.replace(fix.find, fix.replace), context=context)


def apply_corrections(blocks: Sequence[Block], corrections: Sequence[OcrCorrection], doc_id: str) -> List[Block]:
    result = list(blocks)
    for fix in corrections:
        hits = [i for i, b in enumerate(result) if b.page == fix.page for _ in range(_count(b, fix.find))]
        if len(hits) != 1:
            raise CorrectionError(
                f"{doc_id}: correction on page {fix.page} ({fix.find!r} -> {fix.replace!r}) "
                f"matched {len(hits)} times; expected exactly 1"
            )
        target = hits[0]
        result[target] = _apply_one(result[target], fix)
    return result
