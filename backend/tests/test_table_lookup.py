"""District × crop table lookup: when a question names a district and crop, the rate-table
rows for that pair are fetched by their जिल्हा:/पीक: cells and put ahead of the semantic
results, so an embedding miss (short names like बीड) cannot hide the right table."""
import asyncio

from backend.app.services.rag.evidence_index import EvidenceIndex
from backend.app.services.rag.table_lookup import merge_ranked
from backend.tests.gate_fixtures import (
    CORPUS, CORPUS_SCOPE, GADCHIROLI, LEXICON, NAMO_TEXT, NASHIK, PMFBY_TEXT, RATNAGIRI, TABLES, THANE,
)


def positions(question: str):
    return TABLES.positions_for(LEXICON.find(question))


def test_pair_lookup_finds_only_the_matching_tables():
    assert positions("रत्नागिरी जिल्ह्यात भाताची विमा रक्कम?") == (CORPUS.index(RATNAGIRI),)
    assert positions("नाशिकमध्ये कापसासाठी हप्ता?") == (CORPUS.index(NASHIK),)


def test_no_lookup_without_both_a_district_and_a_crop():
    assert positions("रत्नागिरी जिल्ह्यात पीक विमा?") == ()
    assert positions("भाताला किती विमा?") == ()
    assert positions("कर्जमुक्ती योजनेत किती लाभ?") == ()


def test_no_lookup_for_a_pair_absent_from_the_tables():
    assert positions("ठाणे जिल्ह्यात सोयाबीन विमा?") == ()


def test_several_asked_pairs_are_unioned():
    found = positions("नाशिक आणि गडचिरोली जिल्ह्यात कापूस विमा?")
    assert found == tuple(sorted((CORPUS.index(NASHIK), CORPUS.index(GADCHIROLI))))


def test_merge_puts_lookups_first_drops_duplicates_and_caps():
    merged = merge_ranked([RATNAGIRI], [THANE, RATNAGIRI, PMFBY_TEXT, NAMO_TEXT], max_lookups=2, top_k=3)
    assert merged == [RATNAGIRI, THANE, PMFBY_TEXT]


def test_merge_caps_the_number_of_lookup_chunks():
    merged = merge_ranked([RATNAGIRI, THANE, NASHIK], [PMFBY_TEXT], max_lookups=2, top_k=4)
    assert merged == [RATNAGIRI, THANE, PMFBY_TEXT]


def _patch_pipeline(monkeypatch, semantic, seen):
    from backend.app.services.rag import answer_generation as pipeline

    def score_positions(queries, positions):
        return [{**CORPUS[p], "similarity_score": 0.9} for p in positions]

    async def fake_llm(**kwargs):
        seen["chunks"] = kwargs["retrieved_chunks"]
        return {"answer": "उत्तर", "model": "fake", "is_fallback": False}

    monkeypatch.setattr(pipeline.faiss_retriever, "search_multi", lambda **_: semantic)
    monkeypatch.setattr(pipeline.faiss_retriever, "score_positions", score_positions)
    monkeypatch.setattr(pipeline.llm_client, "generate_rag_answer", fake_llm)
    monkeypatch.setattr(pipeline, "current_evidence_index", lambda: EvidenceIndex(LEXICON, CORPUS_SCOPE, TABLES))
    return pipeline


def test_pipeline_answers_from_the_looked_up_table_when_semantic_search_misses_it(monkeypatch):
    seen = {}
    pipeline = _patch_pipeline(monkeypatch, [THANE, PMFBY_TEXT], seen)
    result = asyncio.run(pipeline.answer_government_scheme_query("रत्नागिरी जिल्ह्यात भात पिकासाठी विमा संरक्षित रक्कम किती?"))
    # Thane's table is dropped by the gate; Ratnagiri's comes from the lookup.
    assert [c["chunk_id"] for c in seen["chunks"]] == [RATNAGIRI["chunk_id"], PMFBY_TEXT["chunk_id"]]
    assert result["abstention_reason"] is None


def test_pipeline_lookup_can_be_disabled(monkeypatch):
    seen = {}
    pipeline = _patch_pipeline(monkeypatch, [THANE, PMFBY_TEXT], seen)
    monkeypatch.setattr(pipeline.settings, "TABLE_LOOKUP_ENABLED", False)
    result = asyncio.run(pipeline.answer_government_scheme_query("रत्नागिरी जिल्ह्यात भात पिकासाठी विमा संरक्षित रक्कम किती?"))
    assert result["abstention_reason"] == "evidence_mismatch"
