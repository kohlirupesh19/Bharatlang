"""Numbers in an answer must be traceable to the retrieved evidence (or the question)."""
from backend.app.services.rag.numeric_guard import extract_numbers, normalize_digits, unverified_numbers

EVIDENCE = ["जिल्हा : रत्नागिरी | पीक: भात (तांदूळ); विमा संरक्षित रक्कम (रु.) ६१०००, विमा हप्ता दर (टक्के) ०.७५, "
            "विमा हप्ता रक्कम (रु.) ४५७.५०; खरीप हंगाम २०२५"]


def test_normalize_digits_converts_devanagari():
    assert normalize_digits("६१००० व ०.७५") == "61000 व 0.75"


def test_extract_numbers_canonicalises_grouping_and_decimals():
    assert extract_numbers("रु. ६१,००० आणि 1,00,000 आणि ४५७.५० आणि 457.5") == {"61000", "100000", "457.5"}


def test_correct_answer_has_no_unverified_numbers():
    answer = "रत्नागिरीत भातासाठी विमा संरक्षित रक्कम ₹61,000 प्रति हेक्टर; हप्ता 457.50 रुपये (०.७५%)."
    assert unverified_numbers(answer, EVIDENCE) == ()


def test_misread_amount_is_flagged():
    # the real failure: ६१००० in the evidence came back as "६,१०० रुपये"
    assert unverified_numbers("विमा संरक्षित रक्कम ६,१०० रुपये आहे.", EVIDENCE) == ("6100",)


def test_short_integers_like_list_numbers_are_ignored():
    assert unverified_numbers("1. पात्रता\n2. कागदपत्रे\n३ टप्पे", EVIDENCE) == ()


def test_numbers_from_the_question_are_allowed():
    assert unverified_numbers("२०२६ साठी माहिती उपलब्ध नाही.", EVIDENCE, question="२०२६ मध्ये किती?") == ()


def test_unverified_numbers_are_reported_once_in_order():
    assert unverified_numbers("₹7,500 आणि ₹7500 आणि ₹9,999", EVIDENCE) == ("7500", "9999")


def test_guard_appends_bilingual_warning_only_when_needed():
    from backend.app.services.rag.answer_generation import guard_numbers
    chunks = [{"text": EVIDENCE[0]}]
    ok, ok_flags = guard_numbers("रक्कम 61,000 रुपये.", chunks, "भात?")
    bad, bad_flags = guard_numbers("रक्कम ६,१०० रुपये.", chunks, "भात?")
    assert ok == "रक्कम 61,000 रुपये." and ok_flags == ()
    assert bad_flags == ("6100",)
    assert bad.startswith("रक्कम ६,१०० रुपये.") and "सावधान" in bad and "Caution" in bad and "6100" in bad
