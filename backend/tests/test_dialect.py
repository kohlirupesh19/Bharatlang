import pytest
from backend.app.services.translation.normalization import (
    detect_language_and_dialect,
    normalize_varhadi_to_marathi,
    GLOSSARY_MARATHI_ENGLISH,
    VARHADI_TO_STANDARD_MARATHI
)

def test_varhadi_dialect_detection():
    varhadi_text = "मले शेतीसाठी कर्जमाफी आणि अनुदान कसं भेटन ते सांगा."
    res = detect_language_and_dialect(varhadi_text)
    assert res["primary_language"] == "mr"
    assert "Varhadi" in res["dialect"]
    assert res["is_code_switched"] is False

def test_standard_marathi_detection():
    marathi_text = "नमो शेतकरी महासन्मान निधी योजनेसाठी पात्रता निकष काय आहेत?"
    res = detect_language_and_dialect(marathi_text)
    assert res["primary_language"] == "mr"
    assert "Standard Marathi" in res["dialect"]

def test_non_destructive_varhadi_normalization():
    original = "म्हाले कापूस नुकसानीचे पयशे कवा भेटतील?"
    normalized, replacements = normalize_varhadi_to_marathi(original)
    
    # Original is preserved intact
    assert original == "म्हाले कापूस नुकसानीचे पयशे कवा भेटतील?"
    
    # Normalized replaces dialect markers
    assert "मला" in normalized
    assert "पैसे" in normalized
    assert "केव्हा" in normalized
    
    # Replacements list records exact substitutions
    rep_dict = {r["original"]: r["normalized"] for r in replacements}
    assert rep_dict["म्हाले"] == "मला"
    assert rep_dict["पयशे"] == "पैसे"
    assert rep_dict["कवा"] == "केव्हा"

def test_glossary_presence():
    assert "शेतकरी कर्जमाफी" in GLOSSARY_MARATHI_ENGLISH
    assert "पीक विमा" in GLOSSARY_MARATHI_ENGLISH
    assert "नमो शेतकरी महासन्मान निधी" in GLOSSARY_MARATHI_ENGLISH


# --- Rule-based normalization ------------------------------------------------

def _normalize(text):
    return normalize_varhadi_to_marathi(text)[0]


def test_readme_demo_sentence_is_fully_normalized():
    original = "मला शेतकरी कर्जमाफीचा फायदा व्हाया पायजे, काय करा लागते?"
    assert _normalize(original) == "मला शेतकरी कर्जमाफीचा फायदा व्हायला पाहिजे, काय करावे लागते?"
    assert "Varhadi" in detect_language_and_dialect(original)["dialect"]


@pytest.mark.parametrize("varhadi,standard", [
    ("भेटतील", "मिळतील"),
    ("भेटणार", "मिळणार"),
    ("भेटला", "मिळाला"),
    ("भेटन", "मिळेल"),
    ("भेटाले", "मिळायला"),
    ("करायले", "करायला"),
    ("भरायले", "भरायला"),
    ("कराले", "करायला"),
    ("सांगाले", "सांगायला"),
    ("द्याले", "द्यायला"),
    ("शेतकऱ्याले", "शेतकऱ्याला"),
    ("अधिकाऱ्याले", "अधिकाऱ्याला"),
])
def test_unlisted_word_forms_are_normalized_by_rule(varhadi, standard):
    assert _normalize(varhadi) == standard


@pytest.mark.parametrize("standard_word", [
    "झाले", "आले", "मिळाले", "केले", "गेले", "प्याले",  # standard past tense, not Varhadi
    "भेट", "भेटवस्तू",                                  # noun "visit/gift"
    "रुपये", "शेतकरी", "योजना",
])
def test_standard_words_are_left_alone(standard_word):
    normalized, replacements = normalize_varhadi_to_marathi(standard_word)
    assert normalized == standard_word
    assert replacements == []


def test_noun_before_lagte_is_not_treated_as_obligation_verb():
    assert _normalize("उत्पन्नाचा दाखला लागतो") == "उत्पन्नाचा दाखला लागतो"


def test_obligation_verb_only_rewritten_before_lagne():
    assert _normalize("अर्ज भरा लागते") == "अर्ज भरावे लागते"
    assert _normalize("अर्ज भरा") == "अर्ज भरा"


def test_punctuation_and_danda_do_not_block_matching():
    assert _normalize("(मले) पयशे पायजे।") == "(मला) पैसे पाहिजे।"


@pytest.mark.parametrize("text", [
    "सातबारा उतारा कुठे मिळतो?",
    "मला दोन हजार रुपये कधी मिळतील?",
    "कोणते कागद लागतात आणि खातं कुठे उघडायचं?",
    "अर्ज नाय भरला तर काय होईल?",
])
def test_colloquial_standard_marathi_is_not_flagged_as_varhadi(text):
    assert detect_language_and_dialect(text)["dialect"] == "Standard Marathi"


def test_receive_verb_alone_is_not_enough_for_varhadi():
    res = detect_language_and_dialect("अनुदान कधी भेटणार?")
    assert res["dialect"] == "Standard Marathi"
    assert res["weak_marker_count"] == 1


def test_single_marker_in_long_sentence_is_not_enough():
    text = ("नमो शेतकरी महासन्मान निधी योजनेसाठी अर्ज करताना आधार कार्ड बँक पासबुक "
            "आणि जमिनीचा उतारा ही कागदपत्रे मले लागतील का")
    res = detect_language_and_dialect(text)
    assert res["strong_marker_count"] == 1
    assert res["dialect"] == "Standard Marathi"


def test_single_marker_in_short_sentence_is_enough():
    assert "Varhadi" in detect_language_and_dialect("मले कर्जमाफी कशी मिळेल?")["dialect"]


def test_replacements_record_rule_and_kind():
    _, replacements = normalize_varhadi_to_marathi("शेतकऱ्याले पयशे भेटतील")
    by_original = {r["original"]: r for r in replacements}
    assert by_original["शेतकऱ्याले"]["rule"] == "dative"
    assert by_original["पयशे"]["kind"] == "varhadi"
    assert by_original["भेटतील"]["kind"] == "colloquial_verb"


def test_empty_input():
    assert normalize_varhadi_to_marathi("") == ("", [])
    assert detect_language_and_dialect("   ")["dialect"] == "unknown"

