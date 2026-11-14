"""Read-aloud scoring: does the app keep the meaning and give the right answer?

A person reading aloud skips or changes the odd word; that is fine as long as the meaning
survives. So each clip is judged on (1) whether the asked district/crop and the key phrases
come through, (2) whether the answer has the gold figure (or refuses where it must), and only
diagnostically on WER, where a spelling-tolerant variant counts "दोन हजार पंचवीस" = "2025".
"""
import pytest

from backend.app.evaluation.readaloud import (
    ITEMS, answer_check, loose_normalize, loose_word_errors, meaning_check, parse_paragraphs,
)
from backend.app.evaluation.asr_bench.normalize import normalize_marathi
from backend.app.services.rag.evidence_gate import REFUSAL
from backend.tests.gate_fixtures import LEXICON
from backend.tests.readaloud_fixtures import C02, C03_TRUNCATED_ASR, C07, C08, C08_ASR, C09, C10, V06

PARAGRAPHS = {"C02": C02, "C07": C07, "C08": C08, "C09": C09, "C10": C10, "V06": V06}


# --- loose WER -----------------------------------------------------------------------------

def test_loose_normalize_treats_number_words_and_spelling_variants_as_equal():
    assert loose_normalize("खरीप दोन हजार पंचवीससाठी") == loose_normalize("खरीप 2025 साठी")
    assert loose_normalize("हफ्ता") == loose_normalize("हप्ता")
    assert loose_normalize("माहीत नाही") == loose_normalize("माहित नाही")
    assert loose_normalize("खरिपात") == loose_normalize("खरीपात")


def test_loose_errors_count_only_the_real_mishearing_in_c08():
    strict, loose, words = loose_word_errors(C08, C08_ASR)
    assert loose == 1  # ज्वारीसाठी heard as ज्वालीसाठी
    assert strict > loose
    assert words == len(normalize_marathi(C08).split())


# --- meaning ---------------------------------------------------------------------------------

@pytest.mark.parametrize("item", sorted(PARAGRAPHS))
def test_every_reference_paragraph_passes_its_own_meaning_check(item):
    assert meaning_check(PARAGRAPHS[item], ITEMS[item], LEXICON).kept


def test_real_asr_transcript_with_a_misheard_word_keeps_the_meaning():
    report = meaning_check(C08_ASR, ITEMS["C08"], LEXICON)
    assert report.kept
    assert report.district_ok and report.crop_ok


def test_skipped_context_words_do_not_matter():
    skipped = C08.replace("आणि रब्बीत पुन्हा ज्वारीच", "").replace("काळी कसदार ", "")
    assert meaning_check(skipped, ITEMS["C08"], LEXICON).kept


def test_a_truncated_question_loses_the_meaning():
    # Before pass 14 the ASR cut off "...प्रति हेक्टर किती विमा हप्ता भरावा लागेल".
    report = meaning_check(C03_TRUNCATED_ASR, ITEMS["C03"], LEXICON)
    assert not report.kept
    assert report.missing_phrases  # the premium (हप्ता) is no longer asked
    # With no question left, the last crop mentioned is the onion from the backstory:
    # the app would have looked up the wrong crop.
    # With no question word left, every crop counts as asked, including the backstory's onion:
    # the gate would also demand evidence for onion.
    assert report.heard_crops == ("कांदा", "सोयाबीन")
    assert report.extra_asked == ("कांदा",)


def test_indirect_question_in_the_backstory_does_not_ask_its_crop():
    v03 = ("अकोल्याले आमचं पाच एकराचं वावर हाय. सोयाबीन काढल्यावर आमी हरभरा पेरतो. बँकवाले म्हणते विम्याचे "
           "पयशे आपोआप कापले जाते, पण कितले कापले ते कळत न्हाई. अकोला जिल्ह्यात यंदाच्या खरिपात सोयाबीनची "
           "विमा संरक्षित रक्कम कितली हाय?")
    report = meaning_check(v03, ITEMS["V03"], LEXICON)
    assert report.kept
    assert report.extra_asked == ()  # "हरभरा पेरतो" marks gram as backstory


def test_wrong_crop_heard_loses_the_meaning():
    # C09 asks only at the end: hearing banana there instead of cotton loses the question.
    report = meaning_check(C09.replace("कापसाची विमा", "केळीची विमा"), ITEMS["C09"], LEXICON)
    assert not report.kept and not report.crop_ok
    assert report.heard_crops == ("केळी",)


# --- answers --------------------------------------------------------------------------------

@pytest.mark.parametrize("item, answer, correct", [
    ("C04", "विमा संरक्षित रक्कम प्रति हेक्टर **५९,००० रुपये** आहे.", True),
    ("C04", "विमा संरक्षित रक्कम ५,९०० रुपये आहे.", False),
    ("C03", "शेतकऱ्याचा हप्ता ₹817.50 प्रति हेक्टर (संरक्षित रक्कम ₹54,500).", True),
    ("C08", "विमा संरक्षित रक्कम ₹28,175 आहे.", False),  # the farmer's ₹70.44 is missing
    ("C08", "संरक्षित रक्कम २८,१७५ रुपये व शेतकरी हप्ता ७०.४४ रुपये.", True),
    ("C12", "पहिला हप्ता एप्रिल ते जुलै या काळासाठी, रक्कम २,००० रुपये.", True),
    ("C12", "पहिला हप्ता २,००० रुपये.", False),  # the months are missing
    ("C05", "थकबाकी २ लाख रुपयांपेक्षा जास्त असल्यास लाभ मिळत नाही.", True),
    ("C10", REFUSAL + " ठाणे – सोयाबीन.", True),
    ("C10", "ठाणे जिल्ह्यात सोयाबीनसाठी हप्ता ₹900 आहे.", False),  # a trap must be refused
    ("C04", REFUSAL, False),  # an answerable question must not be refused
    # whole numbers only: a gold figure inside a larger number is not a match (code review, pass 15)
    ("C01", "वर्षाला ३६,००० रुपये, दोन हजारांचे हप्ते.", False),
    ("C01", "वर्षाला ६,००० रुपये, तीन हप्त्यांत २,००० रुपये.", True),
    ("V01", "शेतकऱ्याचा हप्ता ₹5,590 आहे.", False),
    ("V01", "शेतकऱ्याचा हप्ता ₹559 प्रति हेक्टर.", True),
    ("C05", "थकबाकी १२ लाख रुपयांपर्यंत माफ होते.", False),
    ("C08", "संरक्षित रक्कम २८,१७५ रुपये व शेतकरी हप्ता ७०.४४४ रुपये.", False),
])
def test_answer_check(item, answer, correct):
    assert answer_check(answer, ITEMS[item]).correct is correct


# --- specs ----------------------------------------------------------------------------------

def test_every_item_has_gold_figures_or_must_refuse():
    for name, spec in ITEMS.items():
        assert bool(spec.gold) != spec.refuse, name


def test_every_spec_entity_is_known_to_the_lexicon():
    for name, spec in ITEMS.items():
        if spec.district:
            assert LEXICON.find(spec.district).districts == frozenset({spec.district}), name
        if spec.crop:
            assert LEXICON.find(spec.crop).crops == frozenset({spec.crop}), name


def test_paragraphs_are_parsed_from_the_vault_note_format():
    note = ("# Title\n\n## Paragraphs\n\nintro\n\n### C01 · नमो शेतकरी · नाशिक\nनमस्कार. मी शेतकरी आहे.\n\n"
            "EN: Hello.\n\n### V05 · वऱ्हाडी\nमी कर्ज फेडतो.\n\nEN: I repay.\n\n## Gold answers\n| x |")
    assert parse_paragraphs(note) == {"C01": "नमस्कार. मी शेतकरी आहे.", "V05": "मी कर्ज फेडतो."}
