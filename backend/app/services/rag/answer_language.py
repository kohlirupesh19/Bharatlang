"""Answer-language check: is a generated answer Marathi, Hindi or English?

Small local models drift out of Marathi: in the 2026-11-12 bake-off Tiny Aya answered 5 of 12
Marathi questions in English and 1 in Hindi. A script check cannot catch Hindi (it is also
Devanagari), so Devanagari prose is classified by function words that occur in Hindi but not
in Marathi, weighed against Marathi-only words and genitive endings.

The answer template (services/llm/prompts.py) has English section labels and an English
disclaimer, and the refusal sentence is bilingual. Those are removed before counting so a
Marathi answer in the template does not read as English.
"""
import re
from dataclasses import dataclass
from typing import FrozenSet

MARATHI = "mr"
HINDI = "hi"
ENGLISH = "en"
UNKNOWN = "unknown"

# Fewer prose words than this are not classified (e.g. "PMFBY ₹61,000").
MIN_WORDS = 8
# Hindi needs at least this many marker words, and more than the Marathi markers.
MIN_HINDI_MARKERS = 3
# English: Latin words must outnumber Devanagari words by this factor. In the bake-off, English
# answers ran 3.2-4.3x and the most English-heavy Marathi answer 0.27x; the margin leaves room
# for portal names and English document titles in short Marathi answers.
ENGLISH_RATIO = 1.5

_TEMPLATE_LABELS = (
    "SCHEME NAME", "Simple explanation", "Eligibility", "Required documents", "Application procedure",
    "Important conditions", "Source document", "Relevant page", "Last verified date",
    "Information not available",
)
_LABEL = re.compile(r"^[\s>*#\-]*(?:" + "|".join(map(re.escape, _TEMPLATE_LABELS)) + r")[\s*]*:",
                    re.IGNORECASE | re.MULTILINE)
# The template's disclaimer sentence (it may wrap over lines), else just the "Disclaimer:" line;
# never "up to the next blank line", which would also remove prose a model writes after it.
_DISCLAIMER_TEXT = re.compile(
    r"BharatLangTech\s+AI\s+provides\s+informational\s+assistance\b.*?Gram\s+Panchayat\.?",
    re.IGNORECASE | re.DOTALL)
_DISCLAIMER_LINE = re.compile(r"Disclaimer[\s*]*:[^\n]*", re.IGNORECASE)
_URL_OR_EMAIL = re.compile(r"(?:https?://|www\.)\S+|\S+@\S+\.\w+", re.IGNORECASE)
_ENGLISH_REFUSAL = re.compile(
    r"The\s+available\s+official\s+documents\s+do\s+not\s+contain\s+sufficient\s+evidence"
    r"\s+to\s+answer\s+this\s+question\.?", re.IGNORECASE)

_LATIN_WORD = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")
# Devanagari letters and signs only: excludes the dandas (U+0964-5) and digits (U+0966-F).
_DEVANAGARI_WORD = re.compile(r"[ऀ-ॣ॰-ॿ]+")

# Hindi words with no Marathi homograph. Deliberately left out because Marathi uses them too:
# का, की, कि, तो, ही, हो, जो, ये, होता/होती, करता/करते, जाता/जाते, द्वारा, किसान (PM-KISAN),
# and the crop-insurance loanwords बीमा / फसल, which Marathi scheme text also uses.
HINDI_MARKERS: FrozenSet[str] = frozenset(
    "है हैं में और नहीं यह वह वे इस उस इन उन था थे थी गया गई गए हुआ हुई रहा रहे रही "
    "किया किए करें सकते सकता सकती चाहिए को से के लिए भी".split()
)
MARATHI_MARKERS: FrozenSet[str] = frozenset(
    "आहे आहेत आहोत आणि नाही नाहीत असे अशी असेल होईल येईल जाईल केले केली केला करावा करावी "
    "करावे त्यांना यांना व किंवा तसेच परंतु मिळते मिळेल मध्ये साठी".split()
)
_MARATHI_ENDINGS = ("च्या", "ाची", "ाचा", "ाचे", "ेची", "ेचा", "ेचे", "मध्ये", "साठी", "ांना")


@dataclass(frozen=True)
class LanguageVerdict:
    language: str
    devanagari_words: int
    latin_words: int
    hindi_markers: int
    marathi_markers: int


def strip_template(answer: str) -> str:
    """The model's own prose: no template labels, disclaimer or English half of the refusal."""
    text = _DISCLAIMER_TEXT.sub(" ", answer)
    text = _DISCLAIMER_LINE.sub(" ", text)
    text = _URL_OR_EMAIL.sub(" ", text)
    text = _ENGLISH_REFUSAL.sub(" ", text)
    return _LABEL.sub(" ", text)


def _is_acronym(word: str) -> bool:
    return word.isupper() or len(word) == 1


def _is_marathi_marker(word: str) -> bool:
    return word in MARATHI_MARKERS or word.endswith(_MARATHI_ENDINGS)


def detect_answer_language(answer: str) -> LanguageVerdict:
    prose = strip_template(answer)
    latin = [w for w in _LATIN_WORD.findall(prose) if not _is_acronym(w)]
    devanagari = _DEVANAGARI_WORD.findall(prose)
    hindi = sum(w in HINDI_MARKERS for w in devanagari)
    marathi = sum(_is_marathi_marker(w) for w in devanagari)

    if len(latin) + len(devanagari) < MIN_WORDS:
        language = UNKNOWN
    elif len(latin) > ENGLISH_RATIO * len(devanagari):
        language = ENGLISH
    elif hindi >= MIN_HINDI_MARKERS and hindi > marathi:
        language = HINDI
    else:
        language = MARATHI
    return LanguageVerdict(language, len(devanagari), len(latin), hindi, marathi)


def needs_language_retry(verdict: LanguageVerdict, expected: str) -> bool:
    """Only Marathi requests are checked; too-short answers are given the benefit of the doubt."""
    return expected == MARATHI and verdict.language in (HINDI, ENGLISH)
