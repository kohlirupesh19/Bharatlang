import re
from typing import List, Dict, Any, Tuple

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 100

PARAGRAPH_BREAK = re.compile(r'\n\s*\n')
# Sentence ends: Devanagari danda/double danda, Latin punctuation, or a line break.
SENTENCE_BREAK = re.compile(r'(?<=[।॥.!?])\s+|\n+')

PARAGRAPH_JOINER = "\n"
SENTENCE_JOINER = " "


def _hard_split(text: str, max_chars: int) -> List[str]:
    """Splits text with no usable sentence boundary on whitespace, never exceeding max_chars."""
    pieces: List[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            pieces.append(current)
        # A single unbroken token longer than the limit is cut by characters.
        while len(word) > max_chars:
            pieces.append(word[:max_chars])
            word = word[max_chars:]
        current = word
    if current:
        pieces.append(current)
    return pieces


def split_into_units(text: str, max_chars: int) -> List[Tuple[str, str]]:
    """
    Breaks page text into (unit_text, joiner) pairs no longer than max_chars.
    Paragraphs are kept whole when they fit; oversized ones are split by sentence,
    and oversized sentences by whitespace.
    """
    units: List[Tuple[str, str]] = []
    for para in (p.strip() for p in PARAGRAPH_BREAK.split(text)):
        if not para:
            continue
        if len(para) <= max_chars:
            units.append((para, PARAGRAPH_JOINER))
            continue
        for sentence in (s.strip() for s in SENTENCE_BREAK.split(para)):
            if not sentence:
                continue
            if len(sentence) <= max_chars:
                units.append((sentence, SENTENCE_JOINER))
            else:
                units.extend((piece, SENTENCE_JOINER) for piece in _hard_split(sentence, max_chars))
    return units


def _overlap_tail(text: str, overlap: int) -> str:
    """Returns roughly the last `overlap` characters of text, starting at a word boundary."""
    if overlap <= 0 or len(text) <= overlap:
        return ""
    tail = text[-overlap:]
    first_space = tail.find(" ")
    return tail[first_space + 1:] if first_space != -1 else tail


def _pack_units(units: List[Tuple[str, str]], chunk_size: int, chunk_overlap: int) -> List[str]:
    """Greedily packs units into chunk texts of at most chunk_size (+ overlap carried from the previous chunk)."""
    texts: List[str] = []
    current = ""
    for unit, joiner in units:
        if not current:
            current = unit
        elif len(current) + len(joiner) + len(unit) <= chunk_size:
            current = f"{current}{joiner}{unit}"
        else:
            texts.append(current)
            tail = _overlap_tail(current, chunk_overlap)
            current = f"{tail}{joiner}{unit}" if tail else unit
    if current:
        texts.append(current)
    return texts


def chunk_document_pages(
    pages: List[Dict[str, Any]],
    doc_id: str,
    title: str,
    issuing_authority: str = "Government of Maharashtra",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
) -> List[Dict[str, Any]]:
    """
    Chunks extracted page texts into overlapping segments of bounded length
    while preserving strict page numbers, document IDs, and titles.
    No chunk exceeds chunk_size + chunk_overlap characters.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and smaller than chunk_size")

    chunks: List[Dict[str, Any]] = []
    for page_info in pages:
        text = page_info.get("text") or ""
        if not text.strip():
            continue
        page_num = page_info["page"]
        units = split_into_units(text, chunk_size)
        for chunk_text in _pack_units(units, chunk_size, chunk_overlap):
            chunks.append({
                "chunk_id": f"{doc_id}_p{page_num}_c{len(chunks)}",
                "doc_id": doc_id,
                "title": title,
                "page": page_num,
                "text": chunk_text,
                "issuing_authority": issuing_authority
            })
    return chunks


def rechunk_oversized_chunks(
    stored_chunks: List[Dict[str, Any]],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
) -> List[Dict[str, Any]]:
    """
    Re-splits already-indexed chunks that exceed the size limit, leaving
    well-sized chunks untouched. Used to repair an index built before
    oversized paragraphs were split. Returns a new list; the input is not modified.
    """
    max_len = chunk_size + chunk_overlap
    result: List[Dict[str, Any]] = []
    per_doc_counter: Dict[str, int] = {}

    for chunk in stored_chunks:
        doc_id = chunk.get("doc_id")
        text = chunk.get("text", "")
        if len(text) <= max_len:
            pieces = [dict(chunk)]
        else:
            pieces = chunk_document_pages(
                pages=[{"page": chunk.get("page", 1), "text": text}],
                doc_id=doc_id,
                title=chunk.get("title", ""),
                issuing_authority=chunk.get("issuing_authority", "Government of Maharashtra"),
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        for piece in pieces:
            idx = per_doc_counter.get(doc_id, 0)
            per_doc_counter[doc_id] = idx + 1
            result.append({**chunk, **piece, "chunk_id": f"{doc_id}_p{piece.get('page', 1)}_c{idx}"})
    return result
