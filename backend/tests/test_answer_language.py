"""Answer-language check: a Marathi question must get a Marathi answer.

Hindi shares the Devanagari script, so the script alone cannot tell them apart; the answer
template also carries English section labels and an English disclaimer, which must not make a
Marathi answer look English. Fixtures are trimmed from the 2026-11-12 LLM bake-off answers.
"""
import asyncio

import pytest

from backend.app.services.rag.answer_language import detect_answer_language, needs_language_retry

DISCLAIMER = (
    "**Disclaimer:** BharatLangTech AI provides informational assistance based on indexed official "
    "documents and is not an official government authority. Please verify with your local Taluka "
    "Agriculture Officer or Gram Panchayat."
)

# qwen3.5:9b: Marathi prose inside the English template labels.
QWEN_MARATHI = f"""SCHEME NAME: सुधारित प्रधानमंत्री पीक विमा योजना (PMFBY) - खरीप हंगाम 2025

Simple explanation:
रत्नागिरी जिल्ह्यात खरीप हंगाम 2025 मध्ये भात पिकासाठी विमा संरक्षित रक्कम ₹61,000 प्रति हेक्टर आहे.

Eligibility:
- अधिसूचित क्षेत्रात अधिसूचित पीक घेणारे सर्व शेतकरी पात्र आहेत.

Required documents:
- संदर्भात आवश्यक कागदपत्रांची यादी दिलेली नाही.

Source document:
सुधारित प्रधानमंत्री पीक विमा योजना (PMFBY) खरीप हंगाम 2025 व रब्बी हंगाम 2025-26

Information not available:
- अर्ज करण्याची अंतिम तारीख दस्तऐवजात नाही.

{DISCLAIMER}"""

# qwen3.5:9b: its own bilingual refusal followed by Marathi sections.
QWEN_REFUSAL = f"""उपलब्ध शासकीय कागदपत्रांमध्ये या प्रश्नाचे पुरेसे पुरावे उपलब्ध नाहीत. / The available official documents do not contain sufficient evidence to answer this question.

**SCHEME NAME:** General Inquiry (Solar Agriculture Pump Scheme details not found in provided context)

**Simple explanation:**
प्रदान केलेल्या अधिकृत संदर्भात 'सौर कृषी पंप योजना' किंवा त्यातील अनुदानाच्या प्रमाणाबद्दल कोणतीही माहिती उपलब्ध नाही. दिलेला दस्तऐवज फक्त 'सुधारित प्रधानमंत्री पीक विमा योजना (PMFBY)' च्या नुकसान भरपाई सूत्रावर आधारित आहे.

**Eligibility:**
- उपलब्ध दस्तऐवजांमध्ये या योजनेसाठी पात्रता निकष नमूद केलेले नाहीत.

{DISCLAIMER}"""

# Aya Fire Q4: Hindi, in Devanagari.
AYA_HINDI = """**योजना का नाम:** प्रधानमंत्री पीक बीमा योजना (PMFBY)

**सरल व्याख्या:**
PMFBY खरीप 2025 के लिए कपास की फसल के लिए 59,000 रुपये प्रति हेक्टेयर की बीमा संरक्षित राशि प्रदान करता है।

**पात्रता:**
- किसान को PMFBY के लिए पात्र होना चाहिए।
- किसान को कपास की फसल उगानी चाहिए।

**आवेदन प्रक्रिया:**
1. किसान PMFBY के लिए आवेदन करने के लिए अपने ग्राम पंचायत कार्यालय या कृषि कार्यालय में जा सकते हैं।"""

# Aya Fire Q8: English prose; only the scheme name is Marathi.
AYA_ENGLISH = f"""**SCHEME NAME:** सुधारित प्रधानमंत्री पीक विमा योजना (PMFBY)

**Simple explanation:**
PMFBY provides insurance coverage to farmers for crop losses caused by natural calamities, pests and diseases during the Kharif 2025 season.

**Eligibility:**
- All farmers growing notified crops in notified areas are eligible, including sharecroppers and tenant farmers.

**Important conditions:**
- The sum insured for paddy in Ratnagiri district is Rs. 61,000 per hectare.

{DISCLAIMER}"""

# Marathi that uses words Hindi also has (होता, ही, का, की, तो): must not read as Hindi.
MARATHI_SHARED_WORDS = (
    "ही योजना २०१९ मध्ये सुरू झाली होती. शेतकऱ्याने कर्ज वेळेवर फेडले का, हे तपासले जाते. "
    "तो शेतकरी पात्र आहे की नाही हे बँक ठरवते आणि त्याला प्रोत्साहनपर लाभ मिळतो."
)


@pytest.mark.parametrize("answer, language", [
    (QWEN_MARATHI, "mr"),
    (QWEN_REFUSAL, "mr"),
    (AYA_HINDI, "hi"),
    (AYA_ENGLISH, "en"),
    (MARATHI_SHARED_WORDS, "mr"),
])
def test_detects_the_answer_language(answer, language):
    assert detect_answer_language(answer).language == language


def test_marathi_insurance_loanwords_are_not_hindi_markers():
    # बीमा / फसल appear in Marathi crop-insurance text too (code review, pass 13).
    text = "फसल बीमा योजना मध्ये पीक बीमा साठी शेतकरी अर्ज करतात आणि बीमा फसल रक्कम मिळते."
    assert detect_answer_language(text).language == "mr"


def test_urls_and_portal_names_do_not_make_a_marathi_answer_english():
    text = "अर्ज https://pmfby.gov.in/farmer/login वर करा. तसेच Aadhaar card, Maha DBT portal वर नोंदणी करावी."
    assert detect_answer_language(text).language == "mr"


def test_disclaimer_stripping_does_not_swallow_the_prose_after_it():
    answer = ("Disclaimer: this is informational only.\n"
              "PMFBY provides insurance coverage to farmers for crop losses caused by natural calamities, "
              "pests and diseases during the Kharif season in all notified areas of the state.")
    assert detect_answer_language(answer).language == "en"


def test_acronyms_and_template_labels_do_not_count_as_english():
    verdict = detect_answer_language(QWEN_MARATHI)
    assert verdict.latin_words == 0  # PMFBY, the labels and the disclaimer are all excluded


def test_too_little_text_is_unknown_and_not_retried():
    verdict = detect_answer_language("PMFBY ₹61,000")
    assert verdict.language == "unknown"
    assert needs_language_retry(verdict, expected="mr") is False


@pytest.mark.parametrize("answer, retry", [
    (QWEN_MARATHI, False),
    (AYA_HINDI, True),
    (AYA_ENGLISH, True),
])
def test_retry_only_when_a_marathi_question_gets_another_language(answer, retry):
    assert needs_language_retry(detect_answer_language(answer), expected="mr") is retry


def test_other_requested_languages_are_not_policed():
    # Only Marathi answers are checked for now; an English request is left alone.
    assert needs_language_retry(detect_answer_language(AYA_ENGLISH), expected="en") is False


# --- pipeline wiring -------------------------------------------------------------------

CHUNK = {"doc_id": "pmfby-2025", "title": "PMFBY", "page": 8,
         "text": "रत्नागिरी भात विमा संरक्षित रक्कम 61000"}


def _run_generate(monkeypatch, answers):
    from backend.app.services.rag import answer_generation as pipeline
    calls = []

    async def fake_llm(**kwargs):
        calls.append(kwargs)
        return {"answer": answers[len(calls) - 1], "model": "fake", "is_fallback": False}

    monkeypatch.setattr(pipeline.ollama_client, "generate_rag_answer", fake_llm)
    outcome = asyncio.run(pipeline._generate("प्रश्न", "प्रश्न", [CHUNK], "mr"))
    return outcome, calls


def test_marathi_answer_is_kept_with_a_single_llm_call(monkeypatch):
    outcome, calls = _run_generate(monkeypatch, [QWEN_MARATHI])
    assert len(calls) == 1
    assert outcome["answer_language"] == "mr"
    assert outcome["language_retried"] is False


def test_english_answer_is_retried_with_a_marathi_instruction(monkeypatch):
    outcome, calls = _run_generate(monkeypatch, [AYA_ENGLISH, QWEN_MARATHI])
    assert len(calls) == 2
    assert calls[0].get("extra_instruction") is None
    assert "मराठी" in calls[1]["extra_instruction"]
    assert outcome["answer"].startswith("SCHEME NAME: सुधारित")
    assert outcome["answer_language"] == "mr"
    assert outcome["language_retried"] is True


def test_answer_still_not_marathi_after_retry_carries_a_warning(monkeypatch):
    from backend.app.services.rag.answer_generation import LANGUAGE_WARNING_MARKER
    outcome, calls = _run_generate(monkeypatch, [AYA_HINDI, AYA_HINDI])
    assert len(calls) == 2
    assert outcome["answer_language"] == "hi"
    assert outcome["language_retried"] is True
    assert LANGUAGE_WARNING_MARKER in outcome["answer"]


def test_retry_that_falls_back_keeps_the_first_answer_with_a_warning(monkeypatch):
    from backend.app.services.rag import answer_generation as pipeline
    from backend.app.services.rag.answer_generation import LANGUAGE_WARNING_MARKER
    replies = [{"answer": AYA_ENGLISH, "model": "fake", "is_fallback": False},
               {"answer": "Ollama offline. Evidence: …", "model": "fallback", "is_fallback": True}]

    async def fake_llm(**kwargs):
        return replies.pop(0)

    monkeypatch.setattr(pipeline.ollama_client, "generate_rag_answer", fake_llm)
    outcome = asyncio.run(pipeline._generate("प्रश्न", "प्रश्न", [CHUNK], "mr"))
    assert outcome["answer"].startswith(AYA_ENGLISH)
    assert LANGUAGE_WARNING_MARKER in outcome["answer"]
    assert outcome["answer_language"] == "en"
    assert outcome["is_fallback"] is False


def test_retry_with_too_little_text_to_judge_is_accepted(monkeypatch):
    outcome, calls = _run_generate(monkeypatch, [AYA_ENGLISH, "रक्कम ₹61,000"])
    assert len(calls) == 2
    assert outcome["answer"] == "रक्कम ₹61,000"
    assert outcome["answer_language"] == "unknown"


def test_language_check_can_be_disabled(monkeypatch):
    from backend.app.services.rag import answer_generation as pipeline
    monkeypatch.setattr(pipeline.settings, "ANSWER_LANGUAGE_CHECK_ENABLED", False)
    outcome, calls = _run_generate(monkeypatch, [AYA_ENGLISH])
    assert len(calls) == 1
    assert outcome["answer_language"] is None
    assert outcome["language_retried"] is False


def test_rule_based_fallback_is_not_checked(monkeypatch):
    from backend.app.services.rag import answer_generation as pipeline
    calls = []

    async def fallback(**kwargs):
        calls.append(kwargs)
        return {"answer": "Ollama offline. Evidence: रत्नागिरी भात 61000", "model": "fallback", "is_fallback": True}

    monkeypatch.setattr(pipeline.ollama_client, "generate_rag_answer", fallback)
    outcome = asyncio.run(pipeline._generate("प्रश्न", "प्रश्न", [CHUNK], "mr"))
    assert len(calls) == 1
    assert outcome["answer_language"] is None


def test_extra_instruction_is_appended_to_the_prompt():
    from backend.app.services.llm.prompts import build_rag_prompt
    prompt = build_rag_prompt("प्रश्न", [CHUNK], extra_instruction="फक्त मराठीत उत्तर द्या.")
    assert prompt.rstrip().endswith("फक्त मराठीत उत्तर द्या.")
    assert "फक्त मराठीत" not in build_rag_prompt("प्रश्न", [CHUNK])
