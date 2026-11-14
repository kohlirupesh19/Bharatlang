"""The gate and the table lookup act on the crop/district being *asked about*, not every one mentioned.

Farmers give context before the question ("we grow jowar and tur … what is the jowar premium?").
Requiring evidence for every crop named refused answerable questions (read-aloud C08, pass 14).
The asked entity is the last one mentioned before the final question word (ASR output has no
punctuation, so sentences cannot be found), plus any listed directly with it ("नाशिक आणि ठाणे").
"""
import asyncio

import pytest

from backend.app.services.rag.evidence_gate import check_evidence
from backend.app.services.rag.evidence_index import EvidenceIndex
from backend.tests.gate_fixtures import (
    CORPUS, CORPUS_SCOPE, GADCHIROLI, LATUR, LEXICON, NASHIK, PMFBY_TEXT, TABLES, THANE,
)

from backend.tests.readaloud_fixtures import C02, C07, C08, C08_ASR, C09, C10, V06  # noqa: E402


@pytest.mark.parametrize("text, district, crop", [
    (C02, "रत्नागिरी", "भात"),
    (C07, "बीड", "कापूस"),
    (C08, "सोलापूर", "ज्वारी"),
    (C08_ASR, "सोलापूर", "ज्वारी"),  # the final ज्वारीसाठी was misheard; the earlier mention still counts
    (C09, "जळगाव", "कापूस"),
    (C10, "ठाणे", "सोयाबीन"),
    (V06, "बुलढाणा", "डाळिंब"),
])
def test_read_aloud_paragraphs_ask_about_one_district_and_crop(text, district, crop):
    asked = LEXICON.find_asked(text)
    assert asked.districts == frozenset({district})
    assert asked.crops == frozenset({crop})


def test_find_still_reports_every_mention():
    assert LEXICON.find(C08).crops == frozenset({"ज्वारी", "तूर"})


@pytest.mark.parametrize("text, districts, crops", [
    ("नाशिक आणि ठाणे जिल्ह्यात भाताची विमा रक्कम किती?", {"नाशिक", "ठाणे"}, {"भात"}),
    ("नाशिक, ठाणे व रत्नागिरी जिल्ह्यात भात किती?", {"नाशिक", "ठाणे", "रत्नागिरी"}, {"भात"}),
    ("नाशिकमध्ये कापूस आणि सोयाबीनसाठी हप्ता किती?", {"नाशिक"}, {"कापूस", "सोयाबीन"}),
    # A mention after the last question word is enforced too: an aside cannot be told apart
    # from a crop named late ("किती हप्ता आहे ज्वारीचा"), and a refusal is safer than a wrong figure.
    ("नाशिकमध्ये सोयाबीनचा हप्ता किती? आम्ही कापूसही घेतो.", {"नाशिक"}, {"सोयाबीन", "कापूस"}),
    # Each question word asks its own nearest entity (code review, pass 15).
    ("ज्वारीचा हप्ता किती आणि बाजरीचा किती?", set(), {"ज्वारी", "बाजरी"}),
    ("नाशिकमध्ये सोयाबीनचा हप्ता किती आणि पुण्यात किती?", {"नाशिक", "पुणे"}, {"सोयाबीन"}),
    ("ज्वारी का बाजरी चा हप्ता किती?", set(), {"ज्वारी", "बाजरी"}),  # का = "or"
    ("मी तूर पिकवतो, किती हप्ता आहे ज्वारीचा?", set(), {"ज्वारी"}),  # पिकवतो marks tur as backstory
    ("ज्वारी आणि तूर, किती हप्ता आहे ज्वारीचा?", set(), {"ज्वारी", "तूर"}),  # nothing marks tur as backstory
    # Two district-crop pairs before one question: both are asked (code review round 2, pass 15).
    ("ठाण्यात सोयाबीन आणि नाशिकमध्ये कांदा याचा हप्ता किती?", {"ठाणे", "नाशिक"}, {"सोयाबीन", "कांदा"}),
    ("सोयाबीन ठाणे कांदा नाशिक हप्ता किती?", {"ठाणे", "नाशिक"}, {"सोयाबीन", "कांदा"}),
    ("ठाण्यात सोयाबीन आणि नाशिकमध्ये कांदा घेतो, हप्ता किती?", {"ठाणे", "नाशिक"}, {"सोयाबीन", "कांदा"}),
    # A cue inside a question or a condition is not backstory (code review round 3, pass 15).
    ("ठाण्यात सोयाबीन नाही का नाशिकमध्ये कांदा हप्ता किती?", {"ठाणे", "नाशिक"}, {"सोयाबीन", "कांदा"}),
    ("ठाणे सोयाबीन केले तर नाशिक कांदा हप्ता किती?", {"ठाणे", "नाशिक"}, {"सोयाबीन", "कांदा"}),
    ("ठाण्यात सोयाबीन लावल्यास नाशिकमध्ये कांद्याचा हप्ता किती?", {"ठाणे", "नाशिक"}, {"सोयाबीन", "कांदा"}),
    # Backstory marked by a verb is not asked, even when it is the nearest mention to an indirect question.
    ("अकोल्याले सोयाबीन काढल्यावर आमी हरभरा पेरतो. पयशे कितले कापले ते कळत न्हाई. "
     "अकोला जिल्ह्यात सोयाबीनची विमा संरक्षित रक्कम कितली हाय?", {"अकोला"}, {"सोयाबीन"}),
    ("आम्ही ठाण्यात राहतो पण शेती रत्नागिरीत, रत्नागिरी जिल्ह्यात भाताला किती विमा?", {"रत्नागिरी"}, {"भात"}),
    ("किती विमा मिळतो? गडचिरोली, कापूस.", {"गडचिरोली"}, {"कापूस"}),  # nothing before the question word
    ("रत्नागिरी भात", {"रत्नागिरी"}, {"भात"}),  # no question word at all
    ("मी नाशिकचा आहे पण शेती गडचिरोलीत आहे. गडचिरोली जिल्ह्यात कापसाची विमा रक्कम किती?", {"गडचिरोली"}, {"कापूस"}),
    ("कर्जमुक्ती योजनेत किती लाभ मिळतो?", set(), set()),
])
def test_asked_entities_follow_the_question_and_its_lists(text, districts, crops):
    asked = LEXICON.find_asked(text)
    assert asked.districts == frozenset(districts)
    assert asked.crops == frozenset(crops)


# --- gate --------------------------------------------------------------------------------

def gate(question, chunks):
    return check_evidence(question, chunks, LEXICON, CORPUS_SCOPE)


def test_context_crop_without_evidence_does_not_refuse_the_asked_crop():
    question = "गडचिरोलीत आम्ही कापूस आणि थोडी तूर घेतो. गडचिरोली जिल्ह्यात कापसासाठी विमा संरक्षित रक्कम किती?"
    decision = gate(question, [GADCHIROLI])
    assert not decision.abstain
    assert decision.chunks == (GADCHIROLI,)


def test_context_district_without_evidence_does_not_refuse():
    question = "मी नाशिकचा आहे पण शेती गडचिरोलीत आहे. गडचिरोली जिल्ह्यात कापसाची विमा रक्कम किती?"
    decision = gate(question, [GADCHIROLI, NASHIK])
    assert not decision.abstain
    assert decision.chunks == (GADCHIROLI,)  # Nashik's table is about another district


def test_asked_crop_without_evidence_still_refuses_despite_covered_context_crops():
    # C10 shape: Thane grows rice (in the table), but soybean is what is asked.
    question = ("ठाणे जिल्ह्यात आम्ही भात आणि नाचणी घेतो, यंदा सोयाबीन लावायचा आहे. "
                "ठाणे जिल्ह्यात सोयाबीनसाठी किती विमा हप्ता?")
    decision = gate(question, [THANE, LATUR])
    assert decision.abstain
    assert decision.missing == ("ठाणे – सोयाबीन",)


# --- table lookup in the pipeline ------------------------------------------------------------

def test_pipeline_looks_up_and_answers_the_asked_pair_of_a_narrative_question(monkeypatch):
    from backend.app.services.rag import answer_generation as pipeline
    seen, looked_up = {}, []

    def score_positions(queries, positions):
        looked_up.extend(positions)
        return [{**CORPUS[p], "similarity_score": 0.9} for p in positions]

    async def fake_llm(**kwargs):
        seen["chunks"] = kwargs["retrieved_chunks"]
        return {"answer": "उत्तर", "model": "fake", "is_fallback": False}

    monkeypatch.setattr(pipeline.faiss_retriever, "search_multi", lambda **_: [NASHIK, PMFBY_TEXT])
    monkeypatch.setattr(pipeline.faiss_retriever, "score_positions", score_positions)
    monkeypatch.setattr(pipeline.llm_client, "generate_rag_answer", fake_llm)
    monkeypatch.setattr(pipeline, "current_evidence_index", lambda: EvidenceIndex(LEXICON, CORPUS_SCOPE, TABLES))

    result = asyncio.run(pipeline.answer_government_scheme_query(
        "लातूरला आमचे पाहुणे सोयाबीन घेतात. गडचिरोलीत आम्ही कापूस आणि थोडी तूर घेतो. "
        "गडचिरोली जिल्ह्यात कापसासाठी विमा संरक्षित रक्कम किती?"))

    assert looked_up == [CORPUS.index(GADCHIROLI)]  # not Latur × soybean from the context
    assert seen["chunks"][0] is not None and seen["chunks"][0]["chunk_id"] == GADCHIROLI["chunk_id"]
    assert result["abstention_reason"] is None


def test_repeating_the_question_does_not_change_what_is_asked():
    # The pipeline passes "<citizen's words> <normalized words>" to the gate.
    for text in (C08, C10, "ज्वारीचा हप्ता किती आणि बाजरीचा किती?", "मी तूर पिकवतो, किती हप्ता आहे ज्वारीचा?"):
        assert LEXICON.find_asked(f"{text} {text}") == LEXICON.find_asked(text)


@pytest.mark.parametrize("question", [
    "ठाणे जिल्ह्यात सोयाबीनचा हप्ता किती आणि लातूरला किती?",
    "लातूरला सोयाबीनचा हप्ता किती आणि ठाण्यात किती?",
    "मी लातूरचा, किती हप्ता आहे ठाणे जिल्ह्यात सोयाबीनसाठी?",
])
def test_a_second_or_late_named_district_without_evidence_still_refuses(question):
    # Latur has soybean in its table, Thane does not: answering would use Latur's figures.
    decision = gate(question, [LATUR])
    assert decision.abstain
    assert "ठाणे – सोयाबीन" in decision.missing


# --- summary tables must not answer a district × crop question (read-aloud V06) ------------

BULDHANA_SUMMARY = {  # PMFBY p109: notified-circle counts per district; crops are column names, not पीक: cells
    "chunk_id": "pmfby:p109:c594", "chunk_type": "table", "doc_id": "pmfby-2025",
    "text": "प्रधानमंत्री पीक विमा योजना | अधिसूचित मंडळ/तालुक्यांची संख्या, खरीप हंगाम २०२५\n"
            "अ.क्र.: २४; जिल्हा: बुलडाणा; ख.ज्वारी: ९२; सोयाबीन: ९२; मुग: ९२; उडिद: ९२; तुर: ९२; कापूस: ९२; एकूण: ५५२\n"
            "अ.क्र.: २५; जिल्हा: अकोला; ख.ज्वारी: ५२; सोयाबीन: ५२; मुग: ५२; एकूण: ३१२",
}


def test_district_summary_table_does_not_answer_an_absent_crop():
    decision = gate("बुलढाणा जिल्ह्यात डाळिंबासाठी विम्याचा हप्ता कितला आहे?", [BULDHANA_SUMMARY, PMFBY_TEXT])
    assert decision.abstain
    assert decision.missing == ("बुलढाणा – डाळिंब",)


def test_crop_only_procedure_question_is_not_refused_by_the_crop_rule():
    # No district named: rates are not being looked up, so PMFBY prose may answer.
    decision = gate("भात पिकासाठी पीक विमा कसा काढायचा?", [PMFBY_TEXT])
    assert not decision.abstain


def test_two_pairs_before_one_question_refuse_when_either_lacks_evidence():
    decision = gate("ठाण्यात सोयाबीन आणि नाशिकमध्ये कापूस याचा हप्ता किती?", [NASHIK, THANE])
    assert decision.abstain
    assert "ठाणे – सोयाबीन" in decision.missing
