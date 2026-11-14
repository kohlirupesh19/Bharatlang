"""Evidence-match abstention gate: refuse before the LLM when the retrieved tables are about
a different district or crop than the one the question names."""
import asyncio

import pytest

from backend.app.services.rag.entity_lexicon import CROPS, build_lexicon, fold
from backend.app.services.rag.evidence_index import EvidenceIndex
from backend.app.services.rag.evidence_gate import check_evidence

from backend.tests.gate_fixtures import (  # noqa: E402
    CORPUS, CORPUS_SCOPE, GADCHIROLI, KARJ_TEXT, LATUR, LEXICON, NAMO_TEXT, NASHIK, PMFBY_TEXT,
    RATNAGIRI, TABLES, THANE, TITLE, table_chunk,
)


def gate(question: str, chunks):
    return check_evidence(question, chunks, LEXICON, CORPUS_SCOPE)


# --- lexicon ---------------------------------------------------------------------------

def test_fold_merges_common_spelling_variants():
    assert fold("बुलडाणा") == fold("बुलढाणा")
    assert fold("जळगांव") == fold("जळगाव")
    assert fold("सोयाबिन") == fold("सोयाबीन")
    assert fold("लातुर") == fold("लातूर")
    # OCR artefact: a stray consonant + virama before an independent vowel
    assert fold("भुर्ईमूग") == fold("भुईमूग")


@pytest.mark.parametrize("question, district", [
    ("ठाणे जिल्ह्यात भात", "ठाणे"),
    ("ठाण्यात भाताला किती विमा?", "ठाणे"),
    ("नाशिकमध्ये कापूस", "नाशिक"),
    ("रत्नागिरीत भात", "रत्नागिरी"),
    ("साताऱ्यात ज्वारी", "सातारा"),
    ("मुंबई उपनगर जिल्ह्यात भात", "मुंबई"),
    ("मुंबईत भात", "मुंबई"),
    ("छत्रपती संभाजी नगर जिल्ह्यात मका", "छत्रपती संभाजीनगर"),
    ("औरंगाबादेत मका", "छत्रपती संभाजीनगर"),
    ("नाशिकहून आलो", "नाशिक"),
    ("मी पुणेकर शेतकरी", "पुणे"),
    ("औरंगाबाद जिल्ह्यात मका", "छत्रपती संभाजीनगर"),
    ("छत्रपती संभाजीनगर जिल्ह्यातील मका", "छत्रपती संभाजीनगर"),
    ("नागपुरले धान", "नागपूर"),
])
def test_districts_are_found_in_inflected_and_former_names(question, district):
    assert LEXICON.find(question).districts == frozenset({district})


@pytest.mark.parametrize("question, crop", [
    ("भाताला किती विमा", "भात"),
    ("तांदूळ पिकाचा हप्ता", "भात"),
    ("धानाले किती पैसे भेटन", "भात"),
    ("कापसासाठी हप्ता", "कापूस"),
    ("कपाशीला विमा", "कापूस"),
    ("सोयाबिनसाठी", "सोयाबीन"),
    ("गव्हाला किती", "गहू"),
    ("उन्हाळी भुईमुगाला", "भुईमूग"),
    ("तुरीला किती", "तूर"),
    ("तांदळाला किती", "भात"),
    ("द्राक्षांना विमा", "द्राक्ष"),
    ("चणे पिकाला", "हरभरा"),
])
def test_crops_are_found_in_inflected_forms_and_synonyms(question, crop):
    assert LEXICON.find(question).crops == frozenset({crop})


@pytest.mark.parametrize("text", [
    "अन्नधान्य योजनेत मग किती धान्य मिळते?",  # धान्य (grain) is not धान (paddy); मग is not मूग
    "बीडी कामगार",  # bidi, not Beed
    "तूरडाळ स्वस्त धान्य दुकानात",  # तूरडाळ (dal) is not the तूर crop
])
def test_lookalike_words_are_not_entities(text):
    found = LEXICON.find(text)
    assert not found.districts and not found.crops


def test_misspelt_source_label_counts_as_its_crop():
    # the 2025-06-24 GR prints "उ. भुईमगू" in the Nashik rabi table
    lexicon = build_lexicon(["जिल्हा : नाशिक\nअ.क्र.: ५; पीक: उ. भुईमगू; विमा संरक्षित रक्कम (रु.) ४०६००"])
    assert lexicon.find("उ. भुईमगू").crops == frozenset({"भुईमूग"})
    assert {c for _, c in lexicon.crop_forms} == set(CROPS)  # no stray "भुईमगू" crop


def test_crop_lexicon_grows_from_the_corpus():
    lexicon = build_lexicon(["जिल्हा: पुणे\nअ.क्र.: १; पीक: राजगिरा; विमा संरक्षित रक्कम (रु.) ३००००"])
    assert lexicon.find("राजगिऱ्याला विमा").crops == frozenset({"राजगिरा"})


# --- gate decisions --------------------------------------------------------------------

@pytest.mark.parametrize("question, chunks", [
    ("ठाणे जिल्ह्यात खरीप २०२५ मध्ये सोयाबीन पिकासाठी शेतकऱ्याला किती विमा हप्ता भरावा लागेल?", [THANE, LATUR]),
    ("मुंबई उपनगर जिल्ह्यात खरीप २०२५ मध्ये भात पिकाची विमा संरक्षित रक्कम किती आहे?", [THANE, RATNAGIRI]),
    ("रत्नागिरी जिल्ह्यात खरीप २०२५ मध्ये सोयाबीन पिकासाठी विमा संरक्षित रक्कम किती आहे?", [RATNAGIRI, NASHIK]),
])
def test_traps_abstain(question, chunks):
    decision = gate(question, chunks)
    assert decision.abstain
    assert decision.chunks == ()


@pytest.mark.parametrize("question, chunks, kept", [
    ("रत्नागिरी जिल्ह्यात खरीप २०२५ मध्ये भात पिकासाठी विमा संरक्षित रक्कम प्रति हेक्टर किती आहे?",
     [THANE, RATNAGIRI, NAMO_TEXT], [RATNAGIRI, NAMO_TEXT]),
    ("नाशिक जिल्ह्यात खरीप २०२५ साठी कापूस पिकाची विमा संरक्षित रक्कम किती?",
     [GADCHIROLI, NASHIK], [NASHIK]),
    ("गडचिरोली जिल्ह्यात खरीप २०२५ साठी कापूस पिकाची विमा संरक्षित रक्कम किती?",
     [GADCHIROLI, NASHIK], [GADCHIROLI]),
])
def test_lookups_answer_with_wrong_tables_removed(question, chunks, kept):
    decision = gate(question, chunks)
    assert not decision.abstain
    assert list(decision.chunks) == kept


def test_incidental_district_on_a_statewide_scheme_does_not_abstain():
    decision = gate("मी नाशिकचा शेतकरी आहे, नमो शेतकरी योजनेत किती पैसे मिळतात?", [NAMO_TEXT])
    assert not decision.abstain
    assert decision.chunks == (NAMO_TEXT,)


def test_question_without_entities_passes_everything_through():
    decision = gate("कर्जमुक्ती योजनेत जास्तीत जास्त किती लाभ मिळतो?", [NAMO_TEXT, THANE])
    assert not decision.abstain
    assert decision.chunks == (NAMO_TEXT, THANE)


def test_crop_only_question_requires_that_crop_when_tables_are_crop_specific():
    assert gate("डाळिंबासाठी विमा हप्ता किती?", [NASHIK, LATUR]).abstain
    assert not gate("सोयाबीनसाठी विमा हप्ता किती?", [NASHIK, LATUR]).abstain


def test_every_named_district_must_be_covered():
    decision = gate("नाशिक आणि ठाणे जिल्ह्यात भाताची विमा रक्कम किती?", [THANE, NASHIK])
    assert decision.abstain
    assert decision.missing == ("नाशिक – भात",)


def test_refusal_message_names_what_is_missing():
    decision = gate("ठाणे जिल्ह्यात सोयाबीन पिकासाठी विमा हप्ता किती?", [THANE, LATUR])
    assert "उपलब्ध शासकीय कागदपत्रांमध्ये या प्रश्नाचे पुरेसे पुरावे उपलब्ध नाहीत" in decision.refusal_text()
    assert "ठाणे – सोयाबीन" in decision.refusal_text()


def test_trap_still_abstains_alongside_unrelated_statewide_and_same_doc_prose():
    decision = gate("ठाणे जिल्ह्यात सोयाबीन पिकासाठी विमा हप्ता किती?", [LATUR, KARJ_TEXT, PMFBY_TEXT])
    assert decision.abstain
    assert decision.missing == ("ठाणे – सोयाबीन",)


def test_statewide_gr_naming_the_crop_answers_despite_another_districts_table():
    pune_onion = table_chunk("पुणे", ("र. कांदा", "८००००"))
    onion_gr = {"chunk_id": "onion:p1:c2", "chunk_type": "text", "doc_id": "onion-subsidy",
                "text": "कांदा अनुदान योजना\nकांदा उत्पादक शेतकऱ्यांना प्रति क्विंटल रु. ३५० अनुदान देण्यात येईल."}
    decision = gate("नाशिक जिल्ह्यात कांदा अनुदान किती मिळते?", [pune_onion, onion_gr])
    assert not decision.abstain
    assert decision.chunks == (onion_gr,)


def test_table_rows_without_district_context_are_dropped():
    orphan = {"chunk_id": "pmfby:p47:c240", "chunk_type": "table", "doc_id": "pmfby-2025",
              "text": f"{TITLE}\nअ.क्र.: ३; पीक: भात (तांदूळ); विमा संरक्षित रक्कम (रु.) ४९०००"}
    decision = gate("रत्नागिरी जिल्ह्यात भाताची विमा संरक्षित रक्कम किती?", [orphan, RATNAGIRI])
    assert decision.chunks == (RATNAGIRI,)


def test_spelling_variants_in_cells_match_a_clean_question():
    jalgaon = table_chunk("जळगांव", ("भुर्ईमूग", "४२०००"))
    decision = gate("जळगाव जिल्ह्यात भुईमूग विमा रक्कम किती?", [jalgaon])
    assert not decision.abstain and decision.chunks == (jalgaon,)


def test_gate_index_is_rebuilt_when_the_index_changes(monkeypatch):
    from backend.app.services.rag import answer_generation as pipeline
    retriever = pipeline.faiss_retriever
    monkeypatch.setattr(retriever, "metadata_store", [THANE])
    monkeypatch.setattr(retriever, "generation", 10_001)
    assert not pipeline.current_evidence_index().lexicon.find("राजगिरा").crops

    same_size = [table_chunk("पुणे", ("राजगिरा", "३००००"))]
    monkeypatch.setattr(retriever, "metadata_store", same_size)
    monkeypatch.setattr(retriever, "generation", 10_002)
    assert pipeline.current_evidence_index().lexicon.find("राजगिरा").crops == frozenset({"राजगिरा"})


def test_gate_can_be_disabled_for_ab_runs(monkeypatch):
    from backend.app.services.rag import answer_generation as pipeline
    monkeypatch.setattr(pipeline.settings, "EVIDENCE_GATE_ENABLED", False)
    decision = pipeline.gate_evidence("ठाणे जिल्ह्यात सोयाबीन विमा?", [LATUR])
    assert not decision.abstain and decision.chunks == (LATUR,)


# --- pipeline wiring -------------------------------------------------------------------

def test_pipeline_abstains_without_calling_the_llm(monkeypatch):
    from backend.app.services.rag import answer_generation as pipeline

    async def must_not_run(**_):
        raise AssertionError("LLM called despite missing evidence")

    monkeypatch.setattr(pipeline.faiss_retriever, "search_multi", lambda **_: [THANE, LATUR])
    monkeypatch.setattr(pipeline.llm_client, "generate_rag_answer", must_not_run)
    monkeypatch.setattr(pipeline, "current_evidence_index", lambda: EvidenceIndex(LEXICON, CORPUS_SCOPE, TABLES))

    result = asyncio.run(pipeline.answer_government_scheme_query(
        "ठाणे जिल्ह्यात खरीप २०२५ मध्ये सोयाबीन पिकासाठी विमा हप्ता किती?"))

    assert result["is_sufficient_evidence"] is False
    assert result["abstention_reason"] == "evidence_mismatch"
    assert result["llm_model"] is None
    assert result["unverified_numbers"] == []
    assert [s["document_id"] for s in result["sources"]] == ["pmfby-2025", "pmfby-2025"]  # what was searched


def test_pipeline_sends_only_matching_tables_to_the_llm(monkeypatch):
    from backend.app.services.rag import answer_generation as pipeline
    seen = {}

    async def fake_llm(**kwargs):
        seen["chunks"] = kwargs["retrieved_chunks"]
        return {"answer": "रत्नागिरी भात: विमा संरक्षित रक्कम ₹61,000", "model": "fake", "is_fallback": False}

    monkeypatch.setattr(pipeline.faiss_retriever, "search_multi", lambda **_: [THANE, RATNAGIRI])
    monkeypatch.setattr(pipeline.settings, "TABLE_LOOKUP_ENABLED", False)  # gate only; lookup is tested separately
    monkeypatch.setattr(pipeline.llm_client, "generate_rag_answer", fake_llm)
    monkeypatch.setattr(pipeline, "current_evidence_index", lambda: EvidenceIndex(LEXICON, CORPUS_SCOPE, TABLES))

    result = asyncio.run(pipeline.answer_government_scheme_query("रत्नागिरी जिल्ह्यात भात पिकासाठी विमा संरक्षित रक्कम किती?"))

    assert seen["chunks"] == [RATNAGIRI]
    assert result["abstention_reason"] is None
    assert result["unverified_numbers"] == []
    assert len(result["sources"]) == 1


# --- ASR spelling robustness (pass 11) ---------------------------------------------------

@pytest.mark.parametrize("asr_text, district", [
    ("ठाने जिल्ह्यात सोयाबीन", "ठाणे"),  # ण heard as न (seen from AssemblyAI)
    ("पुन्यात कापूस", "पुणे"),
    ("जलगाव जिल्ह्यात कापूस", "जळगाव"),  # targeted ळ→ल alias
])
def test_common_asr_misspellings_still_find_the_district(asr_text, district):
    assert LEXICON.find(asr_text).districts == frozenset({district})


def test_n_retroflex_folding_finds_crops_too():
    assert LEXICON.find("नाचनी पिकाला").crops == frozenset({"नाचणी"})


def test_la_is_not_folded_globally_because_keli_means_did():
    # "केली" (did) would otherwise read as the crop केळी: 135 hits in RESPIN/FLEURS/GR text.
    assert not LEXICON.find("मी अर्ज केली आणि तिला सांगितले").crops
