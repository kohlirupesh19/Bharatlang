"""search() must not collapse different chunks that share a long common prefix (every
chunk of a GR starts with the same title), only exact duplicates."""
import numpy as np

from backend.app.services.rag import retrieval
from backend.app.services.rag.retrieval import FAISSRetriever

TITLE = "सुधारित प्रधानमंत्री पीक विमा योजना (PMFBY) खरीप हंगाम 2025 व रब्बी हंगाम 2025-26 करीता राज्यात राबविणेबाबत"


def _retriever(texts, vectors) -> FAISSRetriever:
    r = FAISSRetriever.__new__(FAISSRetriever)
    r.dimension = 4
    r.generation = 0
    r._init_new_index()
    r.index.add(np.asarray(vectors, dtype="float32"))
    r.metadata_store = [{"chunk_id": f"c{i}", "text": t} for i, t in enumerate(texts)]
    return r


def _unit(*xs):
    v = np.asarray(xs, dtype="float32")
    return v / np.linalg.norm(v)


def test_chunks_sharing_a_long_title_are_all_returned(monkeypatch):
    texts = [f"{TITLE}\nजिल्हा: {d}\nपीक: भात" for d in ("ठाणे", "रत्नागिरी", "रायगड")]
    r = _retriever(texts, [_unit(1, 0.1, 0, 0), _unit(1, 0.2, 0, 0), _unit(1, 0.3, 0, 0)])
    monkeypatch.setattr(retrieval.embedding_engine, "encode_query", lambda q: _unit(1, 0.2, 0, 0))
    results = r.search("q", top_k=3, similarity_threshold=0.0)
    assert sorted(c["chunk_id"] for c in results) == ["c0", "c1", "c2"]


def test_exact_duplicate_texts_are_returned_once(monkeypatch):
    r = _retriever(["एकच मजकूर", "एकच मजकूर", "वेगळा मजकूर"],
                   [_unit(1, 0, 0, 0), _unit(1, 0, 0, 0), _unit(1, 1, 0, 0)])
    monkeypatch.setattr(retrieval.embedding_engine, "encode_query", lambda q: _unit(1, 0, 0, 0))
    results = r.search("q", top_k=3, similarity_threshold=0.0)
    assert [c["text"] for c in results] == ["एकच मजकूर", "वेगळा मजकूर"]


def test_score_positions_ranks_only_the_given_chunks_by_best_query_score(monkeypatch):
    r = _retriever(["अ", "ब", "क"], [_unit(1, 0, 0, 0), _unit(0, 1, 0, 0), _unit(0, 0, 1, 0)])
    vectors = {"q1": _unit(0, 1, 0.2, 0), "q2": _unit(0, 0, 1, 0)}
    monkeypatch.setattr(retrieval.embedding_engine, "encode_query", lambda q: vectors[q])
    ranked = r.score_positions(["q1", "q2", "q1"], [2, 1, 99])  # 99 is out of range
    assert [c["chunk_id"] for c in ranked] == ["c2", "c1"]
    assert ranked[0]["similarity_score"] == 1.0
    assert "similarity_score" not in r.metadata_store[2]  # stored metadata untouched
