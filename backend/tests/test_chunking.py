import pytest
from backend.app.services.rag.chunking import (
    chunk_document_pages,
    rechunk_oversized_chunks,
    split_into_units,
)

SENTENCE = "या योजनेअंतर्गत पात्र शेतकऱ्यांना दरवर्षी सहा हजार रुपये अनुदान दिले जाते."
LONG_PARAGRAPH = " ".join([SENTENCE] * 20)  # one paragraph, no blank lines, ~1500 chars


def _chunk(text, **kwargs):
    return chunk_document_pages([{"page": 3, "text": text}], doc_id="d1", title="T", **kwargs)


def test_oversized_paragraph_is_split_within_limit():
    chunks = _chunk(LONG_PARAGRAPH, chunk_size=500, chunk_overlap=100)
    assert len(chunks) > 1
    assert all(len(c["text"]) <= 600 for c in chunks)
    assert all(c["page"] == 3 and c["doc_id"] == "d1" for c in chunks)


def test_no_content_is_lost_when_splitting():
    chunks = _chunk(LONG_PARAGRAPH, chunk_size=500, chunk_overlap=0)
    assert " ".join(c["text"] for c in chunks) == LONG_PARAGRAPH


def test_consecutive_chunks_overlap():
    chunks = _chunk(LONG_PARAGRAPH, chunk_size=500, chunk_overlap=100)
    tail_word = chunks[0]["text"].split()[-1]
    assert tail_word in chunks[1]["text"][:120]


def test_devanagari_danda_is_a_sentence_boundary():
    text = "पहिले वाक्य आहे। दुसरे वाक्य आहे। तिसरे वाक्य आहे।"
    units = split_into_units(text, max_chars=20)
    assert [u for u, _ in units] == ["पहिले वाक्य आहे।", "दुसरे वाक्य आहे।", "तिसरे वाक्य आहे।"]


def test_text_without_any_boundary_is_hard_split():
    chunks = _chunk("अ" * 1200, chunk_size=500, chunk_overlap=0)
    assert [len(c["text"]) for c in chunks] == [500, 500, 200]


def test_chunk_ids_are_unique():
    chunks = chunk_document_pages(
        [{"page": 1, "text": LONG_PARAGRAPH}, {"page": 2, "text": LONG_PARAGRAPH}],
        doc_id="d1", title="T"
    )
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))


def test_empty_pages_are_skipped():
    assert chunk_document_pages([{"page": 1, "text": "  \n "}], doc_id="d", title="T") == []


@pytest.mark.parametrize("size,overlap", [(0, 0), (100, 100), (100, -1)])
def test_invalid_sizes_are_rejected(size, overlap):
    with pytest.raises(ValueError):
        _chunk("काही मजकूर", chunk_size=size, chunk_overlap=overlap)


def test_rechunk_splits_only_oversized_chunks_and_keeps_input_intact():
    small = {"chunk_id": "d1_p1_c0", "doc_id": "d1", "title": "T", "page": 1,
             "text": SENTENCE, "issuing_authority": "A"}
    big = {"chunk_id": "d1_p2_c1", "doc_id": "d1", "title": "T", "page": 2,
           "text": LONG_PARAGRAPH, "issuing_authority": "A"}
    stored = [small, big]

    result = rechunk_oversized_chunks(stored, chunk_size=500, chunk_overlap=100)

    assert len(stored) == 2 and big["text"] == LONG_PARAGRAPH
    assert result[0]["text"] == SENTENCE
    assert len(result) > 2
    assert all(len(c["text"]) <= 600 for c in result)
    assert all(c["page"] == 2 and c["issuing_authority"] == "A" for c in result[1:])
    ids = [c["chunk_id"] for c in result]
    assert len(ids) == len(set(ids))
